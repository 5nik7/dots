"""Remember successful native runs without granting or persisting approval."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import test_npm_scripts as fixtures
from pkgs_lib import npm_scripts, script_receipts, streams
SPEC=fixtures.SPEC


class Receipts(unittest.TestCase):
    setUp=fixtures.NpmScripts.setUp
    pending=fixtures.NpmScripts.pending
    item=fixtures.NpmScripts.item

    def package(self):
        root=self.home/'global package';root.mkdir()
        (root/'package.json').write_text('{"name":"@scope/tool","version":"1.2.3","scripts":{"postinstall":"node build.js"}}')
        (root/'build.js').write_text('fixture')
        record=json.dumps(dict(name='@scope/tool',version='1.2.3',path=str(root),scripts={'postinstall':'node build.js'}),sort_keys=True)
        return root,{SPEC:[record]}

    def test_verified_run_is_remembered_and_missing_output_prompts_again(self):
        root,metadata=self.package();output=self.pending()
        def run(*args,**kwargs):
            (root/'built.node').write_text('compiled')
            output.pending.observe('npm info run '+SPEC+' postinstall { code: 0, signal: null }')
            return 0
        with patch.object(npm_scripts,'terminal',return_value=True),patch.object(npm_scripts,'evidence',return_value=metadata), \
             patch.object(npm_scripts,'approve',return_value=True) as approve,patch.object(streams,'run',side_effect=run) as rebuild, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),0)
            output=self.pending()
            self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),0)
            self.assertEqual(output.pending.current,[SPEC]);self.assertEqual(output.pending.ran,[])
            self.assertEqual(approve.call_count,1);self.assertEqual(rebuild.call_count,1)
            (root/'built.node').unlink()
            output=self.pending();self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),0)
            self.assertEqual(approve.call_count,2);self.assertEqual(rebuild.call_count,2)

    def test_reinstall_metadata_file_drift_corrupt_receipts_and_new_version(self):
        root,metadata=self.package();proof=script_receipts.fingerprint(metadata[SPEC])
        script_receipts.save(SPEC,proof);self.assertTrue(script_receipts.matches(SPEC,proof))
        same=(root/'package.json').read_bytes();(root/'package.json').unlink();(root/'package.json').write_bytes(same)
        self.assertFalse(script_receipts.matches(SPEC,script_receipts.fingerprint(metadata[SPEC])))
        self.assertFalse(script_receipts.matches('@scope/tool@2.0.0',proof))
        script_receipts.location(SPEC).write_text('{bad')
        self.assertFalse(script_receipts.matches(SPEC,proof))
        outside=self.home/'outside';outside.write_text('external')
        (root/'external').symlink_to(outside)
        self.assertIsNone(script_receipts.fingerprint(metadata[SPEC]))

    def test_receipts_never_approve_missing_or_drifted_scripts_without_terminal(self):
        root,metadata=self.package();proof=script_receipts.fingerprint(metadata[SPEC]);script_receipts.save(SPEC,proof)
        with patch.object(npm_scripts,'terminal',return_value=False),patch.object(npm_scripts,'evidence',return_value=metadata), \
             patch.object(npm_scripts,'approve') as approve,patch.object(streams,'run') as run:
            output=self.pending();self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),0)
            self.assertEqual(output.pending.current,[SPEC])
            (root/'build.js').write_text('changed')
            output=self.pending();self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),0)
            self.assertEqual(output.pending.current,[])
        approve.assert_not_called();run.assert_not_called()

    def test_file_change_during_approval_refuses_rebuild(self):
        root,metadata=self.package();output=self.pending()
        def approve(spec): (root/'build.js').write_text('changed');return True
        with patch.object(npm_scripts,'terminal',return_value=True),patch.object(npm_scripts,'evidence',return_value=metadata), \
             patch.object(npm_scripts,'approve',side_effect=approve),patch.object(streams,'run') as run,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(output.pending.review(self.item(),self.cfg,output,0),1)
        run.assert_not_called();self.assertFalse(script_receipts.location(SPEC).exists())


if __name__=='__main__':unittest.main()
