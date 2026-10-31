#!/usr/bin/env python3
"""Preparation ordering, stale guards and dry-run boundaries in owned roots."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

import test_installation as fixtures
sys.path.insert(0,str(fixtures.ROOT/'plugins/pkgs'))
from install import Installation, main
from setup_stages import Preparation
from pkgs_lib import manifests


class SetupStages(unittest.TestCase):
    setUp=fixtures.InstallationTests.setUp
    write=fixtures.InstallationTests.write

    def args(self):
        return SimpleNamespace(component=['packages'],packages=None,with_dependencies=False,json=True,
            package_document=dict(schema=1,groups=[dict(manager='npm',scope='global',packages=[dict(name='fixture')])]))

    def test_dry_run_never_queries_managers_or_prepares_payloads(self):
        path=self.base/'packages.json';path.write_text(json.dumps(self.args().package_document))
        out=io.StringIO()
        with patch.dict(os.environ,self.env),redirect_stdout(out),patch('pkgs_lib.manifests.prepare',side_effect=AssertionError('manager probe')):
            self.assertEqual(main(['install','--component','packages','--packages',str(path),'--dry-run','--json']),0)
        self.assertEqual(json.loads(out.getvalue())['preparation'][0]['stage'],'packages')
        self.assertFalse((self.home/'.state').exists())
        self.assertFalse((self.home/'.cache').exists())

    def test_first_failure_retains_record_and_stops_later_preparation(self):
        with patch.dict(os.environ,self.env):
            installation=Installation(self.repo);stage=Preparation(installation,self.args())
            stage.leaf=Mock()
            fake=Mock();fake.apply.return_value=dict(schema=1,status='incomplete',groups=[])
            with patch('package_setup.Stage',return_value=fake),self.assertRaisesRegex(ValueError,'incomplete'):
                stage.run()
            stage.leaf.prepare.assert_not_called()
            self.assertFalse(installation.receipt_path.exists())
            self.assertEqual(json.loads(stage.record.read_text())['stages'][-1]['status'],'failed')

    def test_stale_inputs_stop_before_external_stage(self):
        with patch.dict(os.environ,self.env):
            installation=Installation(self.repo);installation.guard(self.source)
            stage=Preparation(installation,self.args());self.source.write_text('changed')
            with patch('package_setup.Stage') as backend,self.assertRaisesRegex(ValueError,'changed after preview'):
                stage.run()
            backend.assert_not_called();self.assertFalse(stage.record.exists())

    def test_satisfied_packages_do_not_create_preparation_records(self):
        with patch.dict(os.environ,self.env):
            installation=Installation(self.repo);stage=Preparation(installation,self.args())
            fake=Mock();fake.apply.return_value=dict(schema=1,status='complete',groups=[dict(status='unchanged')])
            with patch('package_setup.Stage',return_value=fake):stage.run()
            self.assertEqual(stage.outcomes[0]['status'],'complete')
            self.assertFalse(stage.record.exists());self.assertFalse(installation.state.exists())

    def test_manifest_stop_on_first_group_failure(self):
        document=dict(schema=1,groups=[dict(manager='npm',scope='global',packages=[dict(name='one')]),
                                      dict(manager='pip',scope='base',packages=[dict(name='two')])])
        def failed(group,cfg,**kwargs):return dict(group=group,status='deferred',reason='fixture missing manager',plan=None)
        with patch('pkgs_lib.manifests.prepare_group',side_effect=failed) as prepare:
            result=manifests.apply(document,{},stop_on_failure=True)
        self.assertEqual(prepare.call_count,1);self.assertEqual(result['status'],'incomplete')


if __name__=='__main__':unittest.main(verbosity=2)
