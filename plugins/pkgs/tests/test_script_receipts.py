"""Remember successful native runs without granting or persisting approval."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import test_npm_scripts as fixtures
from pkgs_lib import npm_scripts, script_receipts, streams
from pkgs_lib.common import Error
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

    def nested(self):
        root, metadata = self.package()
        child = 'node-pty@1.1.0'
        nested = root/'node_modules'/'node-pty'; nested.mkdir(parents=True)
        manifest = dict(name='node-pty', version='1.1.0', scripts={'postinstall': 'node build.js'})
        (nested/'package.json').write_text(json.dumps(manifest))
        (nested/'build.js').write_text('fixture')
        metadata[child] = [json.dumps(dict(manifest, path=str(nested)), sort_keys=True)]
        return root, nested, child, metadata

    def test_parent_and_dependency_receipts_match_after_full_batch(self):
        root, nested, child, metadata = self.nested()
        output = self.pending(); output.pending.specs.add(child)
        def evidence(specs, env=None): return {spec: metadata[spec] for spec in specs}
        def run(command, *args, **kwargs):
            spec = command[-1]
            (nested if spec == child else root).joinpath('built.node').write_text('compiled')
            output.pending.observe('npm info run '+spec+' postinstall { code: 0, signal: null }')
            return 0
        with patch.object(npm_scripts, 'terminal', return_value=True), \
             patch.object(npm_scripts, 'evidence', side_effect=evidence), \
             patch.object(npm_scripts, 'approve', return_value=True) as approve, \
             patch.object(streams, 'run', side_effect=run) as rebuild, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(output.pending.review(self.item(), self.cfg, output, 0), 0)
            for spec in metadata:
                self.assertTrue(script_receipts.matches(spec, script_receipts.fingerprint(metadata[spec])))
            output = self.pending(); output.pending.specs.add(child)
            self.assertEqual(output.pending.review(self.item(), self.cfg, output, 0), 0)
            self.assertEqual(output.pending.current, sorted(metadata))
            self.assertEqual(approve.call_count, 2); self.assertEqual(rebuild.call_count, 2)

    def test_failed_interrupted_unconfirmed_or_declined_child_is_never_receipted(self):
        for failure in ('failed', 'interrupted', 'unconfirmed', 'declined'):
            with self.subTest(failure=failure):
                # Use distinct owned roots for each batch.
                with patch.object(self, 'home', self.home/failure):
                    self.home.mkdir()
                    root, nested, child, metadata = self.nested()
                output = self.pending(); output.pending.specs.add(child)
                def evidence(specs, env=None): return {spec: metadata[spec] for spec in specs}
                def run(command, *args, **kwargs):
                    spec = command[-1]
                    if spec == child:
                        if failure == 'failed': return 7
                        if failure == 'interrupted': return 130
                        if failure == 'unconfirmed': return 0
                    (nested if spec == child else root).joinpath('built.node').write_text('compiled')
                    output.pending.observe('npm info run '+spec+' postinstall { code: 0, signal: null }')
                    return 0
                with patch.object(npm_scripts, 'terminal', return_value=True), \
                     patch.object(npm_scripts, 'evidence', side_effect=evidence), \
                     patch.object(npm_scripts, 'approve', side_effect=lambda s: not (s == child and failure == 'declined')), \
                     patch.object(streams, 'run', side_effect=run), contextlib.redirect_stdout(io.StringIO()):
                    if failure == 'interrupted':
                        with self.assertRaises(KeyboardInterrupt): output.pending.review(self.item(), self.cfg, output, 0)
                    else:
                        self.assertEqual(output.pending.review(self.item(), self.cfg, output, 0),
                                         {'failed': 7, 'unconfirmed': 1, 'declined': 0}[failure])
                self.assertFalse(script_receipts.location(child).exists())
                self.assertEqual(script_receipts.location(SPEC).exists(), failure == 'declined')

    def test_final_receipt_failure_never_claims_unverified_evidence(self):
        root, metadata = self.package()
        for failure in ('metadata', 'query', 'fingerprint', 'write'):
            output = self.pending()
            def evidence(specs, env=None):
                if output.pending.ran:
                    if failure == 'metadata': return {SPEC: ['changed metadata']}
                    if failure == 'query': raise Error('fixture inventory failure')
                return metadata
            def run(*args, **kwargs):
                output.pending.observe('npm info run '+SPEC+' postinstall { code: 0, signal: null }')
                return 0
            fingerprint = script_receipts.fingerprint
            with self.subTest(failure=failure), patch.object(npm_scripts, 'terminal', return_value=True), \
                 patch.object(npm_scripts, 'evidence', side_effect=evidence), \
                 patch.object(npm_scripts, 'approve', return_value=True), \
                 patch.object(streams, 'run', side_effect=run), \
                 patch.object(script_receipts, 'fingerprint', side_effect=lambda r: None if failure == 'fingerprint' and output.pending.ran else fingerprint(r)), \
                 patch.object(script_receipts, 'save', side_effect=OSError('fixture write failure')) as save, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(output.pending.review(self.item(), self.cfg, output, 0), 0)
            self.assertEqual(output.pending.ran, [SPEC])
            self.assertEqual(save.call_count, failure == 'write')
            self.assertFalse(script_receipts.location(SPEC).exists())
            self.assertTrue(any('receipt unavailable' in warning for warning in output.warnings))


if __name__=='__main__':unittest.main()
