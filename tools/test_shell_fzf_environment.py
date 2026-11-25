"""Check the published FZF preview and caller overrides in disposable native PTYs."""
import json
import os
from pathlib import Path
import sys
import unittest

if os.name != 'nt':
    from bench_shell_readiness import ROOT, interactive_fixture, wait_for_output
    from test_shell_init import executable
    from zsh_interactive import Session


def publication(home, preview):
    state = home/'state/dots/themes'
    generation = state/'generations/g.fixture'
    generation.mkdir(parents=True)
    (state/'current').write_text('g.fixture\n')
    (state.parent/'current').mkdir()
    (state.parent/'current/theme').symlink_to(generation, target_is_directory=True)
    (generation/'shell.tsv').write_text('@theme\tid\tfixture\n@theme\tfamily\tfixture\n@theme\tflavor\tdark\n'
                                        '@palette\tblue\t#112233\n@role\tforeground\t#ffffff\n')
    (generation/'init.zsh').write_text("declare -gA dots_roles=([foreground]=white [muted]=blue [accent]=cyan [warning]=yellow)\n"
                                       "export DOTS_THEME_ID=fixture DOTS_THEME_FAMILY=fixture FLAVOR=dark\n")
    opts = '--pointer=▎' + (' --preview=' if preview else '')
    (generation/'visual.tsv').write_text('env\tDOTS_THEME_FZF_COLORS\tfg:#123456\n'
                                          f'env\tDOTS_THEME_FZF_OPTS\t{opts}\n'
                                          f'env\tDOTS_THEME_FZF_PREVIEW\t{int(preview)}\n', encoding='utf-8')


@unittest.skipIf(os.name == 'nt', 'PTY coverage is POSIX; PowerShell uses its native fixture')
class FzfEnvironment(unittest.TestCase):
    def test_published_and_caller_preview_options(self):
        for shell in ('bash', 'zsh', 'fish', 'nu', 'xonsh'):
            if not executable(shell):
                continue
            for mode in ('options', 'file', 'configured-empty', 'default'):
                with self.subTest(shell=shell, mode=mode), interactive_fixture(ROOT, shell, installed=True) as (env, home, argv, _):
                    env['DOTS_INIT_THEME'] = '1'
                    publication(home, mode == 'configured-empty')
                    if mode == 'options':
                        env['FZF_DEFAULT_OPTS'] = "--height=29% --preview='my fixture {}'"
                    elif mode == 'file':
                        options_file = home/'fixture ü.opts'
                        options_file.write_text("--preview='my file fixture {}'\n", encoding='utf-8')
                        env['FZF_DEFAULT_OPTS_FILE'] = str(options_file)
                    command = Path(env['PATH'])/'fixture-fzf-env'
                    command.write_text(f'#!{sys.executable}\nimport json,os\nfrom pathlib import Path\n'
                                       'keys = ["FZF_DEFAULT_OPTS","FZF_DEFAULT_OPTS_FILE","DOTS_THEME_FZF_COLORS"]\n'
                                       'Path(os.environ["HOME"],"result").write_text(json.dumps([os.getenv(k) for k in keys]))\n'
                                       'print("__FZF_DONE__")\n')
                    command.chmod(0o700)
                    session = Session(env, home, argv=argv)
                    try:
                        if shell == 'xonsh':
                            wait_for_output(session, b'\x1b[?2004h')
                            session.send('\x15')
                        session.send('fixture-fzf-env\r')
                        wait_for_output(session, b'__FZF_DONE__', timeout=30)
                        opts, filename, palette = json.loads((home/'result').read_text())
                        self.assertEqual(palette, 'fg:#123456')
                        if mode in ('options', 'file'):
                            self.assertEqual(opts, env.get('FZF_DEFAULT_OPTS'))
                            self.assertEqual(filename, env.get('FZF_DEFAULT_OPTS_FILE'))
                        else:
                            self.assertIn('--pointer=▎', opts)
                            self.assertIn('--color=fg:#123456', opts)
                            self.assertEqual('_dots-fzf-preview --selection {f}' in opts, mode == 'default')
                    finally:
                        session.close()


if __name__ == '__main__':
    unittest.main()
