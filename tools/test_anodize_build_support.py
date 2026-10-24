#!/usr/bin/env python3
"""Build-environment isolation checks; no compiler invocation is required."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from anodize_build_support import environment, tool


class BuildEnvironmentTests(unittest.TestCase):
    def test_offline_roots_and_telemetry_are_owned(self):
        with tempfile.TemporaryDirectory(prefix='anodize build ü ') as temporary:
            root = Path(temporary).resolve()
            compiler = root / 'toolchain/go'
            poison = dict(HOME='/unowned', GOTOOLCHAIN='auto', GOPROXY='https://invalid.example',
                          GOFLAGS='-race', GOWORK='/unowned/go.work', SECRET_SENTINEL='unowned')
            inherited = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR') if key in os.environ}
            with patch.dict(os.environ, dict(poison, **inherited), clear=True):
                env = environment(root, compiler)
                self.assertEqual(os.environ['HOME'], '/unowned')
            for key in ('HOME', 'USERPROFILE', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME',
                        'XDG_CACHE_HOME', 'APPDATA', 'LOCALAPPDATA', 'TMPDIR', 'TMP', 'TEMP',
                        'GOPATH', 'GOMODCACHE', 'GOCACHE', 'GOTMPDIR', 'DOTS'):
                self.assertTrue(Path(env[key]).is_relative_to(root), key)
            for key in ('GOENV', 'GOWORK', 'GOPROXY', 'GOSUMDB'):
                self.assertEqual(env[key], 'off')
            self.assertEqual(env['GOVCS'], '*:off')
            self.assertEqual(env['GOTOOLCHAIN'], 'local')
            self.assertEqual(env['PATH'], str(compiler.parent))
            self.assertEqual(env['CGO_ENABLED'], '0')
            self.assertEqual((root / 'config/go/telemetry/mode').read_text(), 'off\n')
            self.assertNotIn('SECRET_SENTINEL', env)
            if os.name == 'nt':
                self.assertEqual(env['HOMEDRIVE'] + env['HOMEPATH'], env['USERPROFILE'])
                for key, value in inherited.items():
                    self.assertEqual(env[key], value)

    def test_missing_tool_is_reported_without_installation(self):
        with patch('anodize_build_support.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'nothing was installed'):
                tool('missing-fixture-compiler')


if __name__ == '__main__':
    unittest.main()
