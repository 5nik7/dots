#!/usr/bin/env python3
"""Pinned build orchestration; fixture tools never install or fetch host data."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_installation as fixtures
from install import Installation
from setup_leaf import Build, COMMIT, VERSION


class SetupLeaf(unittest.TestCase):
    setUp = fixtures.InstallationTests.setUp
    write = fixtures.InstallationTests.write

    def fixture(self):
        (self.repo/'tools/patches').mkdir(parents=True)
        (self.repo/'tools/patches/leaf-1.28.2-dots-syntax.patch').write_text('fixture patch')
        (self.repo/'tools/test_leaf_theme.py').write_text('fixture consumer')
        self.sysroot = self.base/'rust toolchain'
        (self.sysroot/'bin').mkdir(parents=True)
        self.suffix = '.exe' if os.name == 'nt' else ''
        for tool in ('cargo','rustc'): (self.sysroot/'bin'/(tool+self.suffix)).write_text('fixture')
        self.calls = []

    def execute(self, argv, *, cwd=None, env=None, capture=False):
        words = list(map(str,argv));self.calls.append(words)
        if words == ['rustc','--print','sysroot']: return str(self.sysroot)
        if words[-1] == '-vV': return 'fixture rustc 1.90'
        if words[-1] == '-V': return 'fixture cargo 1.90'
        if words[-1] == '--version': return VERSION
        if words[:2] == ['git','init']:
            Path(words[-1]).mkdir();(Path(words[-1])/'.git').mkdir()
        if words[0] == 'git': self.assertNotIn('GIT_DIR',env)
        if 'checkout' in words: (Path(words[2])/'main.rs').write_text('original')
        if 'rev-parse' in words: return COMMIT
        if 'status' in words: return ''
        if 'apply' in words and '--check' not in words:
            (Path(words[2])/'main.rs').write_text('patched')
        if 'cargo'+self.suffix == Path(words[0]).name:
            self.assertEqual(env['CARGO_HOME'],str(Path(env['CARGO_TARGET_DIR']).parent/'cargo'))
            self.assertNotEqual(env['HOME'],str(self.home))
            self.assertIn('--locked',words)
            if 'build' in words:
                binary=Path(env['CARGO_TARGET_DIR'])/'release'/('leaf'+self.suffix)
                binary.parent.mkdir(parents=True);binary.write_bytes(b'verified fixture binary')
                binary.chmod(0o755)
        return ''

    def test_pinned_build_reuse_publication_and_original_restore(self):
        self.fixture()
        with patch.dict(os.environ,self.env),patch('setup_leaf.execute',side_effect=self.execute):
            original=self.home/'.local/bin'/('leaf'+self.suffix);original.parent.mkdir(parents=True);original.write_bytes(b'original leaf')
            installation=Installation(self.repo)
            build=Build(installation)
            result=build.prepare()
            self.assertFalse(result['reused'])
            self.assertTrue(any(COMMIT in call and 'fetch' in call for call in self.calls))
            self.assertTrue(any('clippy' in call and '--all-targets' in call for call in self.calls))
            count=len(self.calls)
            self.assertTrue(Build(installation).prepare()['reused'])
            self.assertFalse(any('fetch' in call or 'build' in call for call in self.calls[count:]))
            build.publish(installation);installation.apply('install')
            self.assertEqual(original.read_bytes(),b'verified fixture binary')
            removal=Installation(self.repo);removal.plan_uninstall(['leaf']);removal.apply('uninstall')
            self.assertEqual(original.read_bytes(),b'original leaf')

    def test_build_failure_never_publishes_and_cache_drift_refuses(self):
        self.fixture()
        def fail(argv,**kwargs):
            if 'clippy' in argv: raise ValueError('fixture compiler failure')
            return self.execute(argv,**kwargs)
        with patch.dict(os.environ,self.env),patch('setup_leaf.execute',side_effect=fail):
            installation=Installation(self.repo);build=Build(installation)
            with self.assertRaisesRegex(ValueError,'compiler failure'):build.prepare()
            self.assertFalse(build.target.exists());self.assertFalse(installation.receipt_path.exists())
            self.assertFalse(list(build.base.rglob('verified.json')))
        with patch.dict(os.environ,self.env),patch('setup_leaf.execute',side_effect=self.execute):
            build=Build(Installation(self.repo));result=build.prepare()
            Path(result['path']).write_text('changed artifact')
            with self.assertRaisesRegex(ValueError,'cache changed'):Build(Installation(self.repo)).prepare()

    def test_failed_fetch_resumes_owned_empty_repository(self):
        self.fixture()
        failed=False
        def acquire(argv,**kwargs):
            nonlocal failed
            if 'fetch' in argv and not failed:
                failed=True
                raise ValueError('fixture network failure')
            return self.execute(argv,**kwargs)
        with patch.dict(os.environ,dict(self.env,GIT_DIR='/unrelated/repository')),patch('setup_leaf.execute',side_effect=acquire):
            with self.assertRaisesRegex(ValueError,'network failure'):
                Build(Installation(self.repo)).prepare()
            result=Build(Installation(self.repo)).prepare()
            self.assertFalse(result['reused']);self.assertTrue(Path(result['path']).is_file())

    def test_failed_stages_preserve_existing_command(self):
        for stage in ('fetch', 'apply', 'test', 'clippy', 'build', 'consumer'):
            with self.subTest(stage=stage):
                case=SetupLeaf();case.setUp()
                try:
                    case.fixture()
                    original=case.home/'.local/bin'/('leaf'+case.suffix);original.parent.mkdir(parents=True)
                    original.write_bytes(b'original leaf')
                    def fail(argv,**kwargs):
                        words=list(map(str,argv))
                        if ((stage=='consumer' and str(case.repo/'tools/test_leaf_theme.py') in words)
                                or (stage!='consumer' and stage in words and '--check' not in words)):
                            raise ValueError('fixture stage failure')
                        return case.execute(argv,**kwargs)
                    with patch.dict(os.environ,case.env),patch('setup_leaf.execute',side_effect=fail):
                        installation=Installation(case.repo);build=Build(installation)
                        with self.assertRaisesRegex(ValueError,'stage failure'):build.prepare()
                        self.assertEqual(original.read_bytes(),b'original leaf')
                        self.assertFalse(installation.receipt_path.exists())
                        self.assertFalse(list(build.base.rglob('verified.json')))
                        with self.assertRaisesRegex(ValueError,'artifact changed'):build.publish(installation)
                finally:case.doCleanups()

    def test_foreign_command_link_is_refused_before_acquisition(self):
        self.fixture()
        original=self.home/'.local/bin'/('leaf'+self.suffix);original.parent.mkdir(parents=True)
        foreign=self.base/'foreign leaf';foreign.write_bytes(b'foreign command')
        original.symlink_to(foreign)
        with patch.dict(os.environ,self.env),patch('setup_leaf.execute',side_effect=self.execute):
            installation=Installation(self.repo)
            with self.assertRaisesRegex(ValueError,'unrelated link'):Build(installation)
            self.assertEqual(self.calls,[])
            self.assertEqual(original.resolve(),foreign)
            self.assertEqual(foreign.read_bytes(),b'foreign command')
            self.assertFalse(installation.receipt_path.exists())

    def test_changed_source_after_failed_build_is_preserved(self):
        self.fixture()
        original=self.home/'.local/bin'/('leaf'+self.suffix);original.parent.mkdir(parents=True)
        original.write_bytes(b'original leaf')
        def fail(argv,**kwargs):
            if 'clippy' in argv:raise ValueError('fixture compiler failure')
            return self.execute(argv,**kwargs)
        with patch.dict(os.environ,self.env):
            installation=Installation(self.repo);build=Build(installation)
            with patch('setup_leaf.execute',side_effect=fail),self.assertRaisesRegex(ValueError,'compiler failure'):
                build.prepare()
            source=next(build.base.glob('*/source/main.rs'));source.write_text('user source edit')
            self.calls.clear()
            with patch('setup_leaf.execute',side_effect=self.execute),self.assertRaisesRegex(ValueError,'source changed'):
                Build(Installation(self.repo)).prepare()
            self.assertFalse(any('fetch' in call or 'test' in call or 'build' in call for call in self.calls))
            self.assertEqual(source.read_text(),'user source edit')
            self.assertEqual(original.read_bytes(),b'original leaf')
            self.assertFalse(installation.receipt_path.exists())
            self.assertFalse(list(build.base.rglob('verified.json')))


if __name__ == '__main__': unittest.main(verbosity=2)
