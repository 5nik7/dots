"""Private Zsh types preserve literal provider records and native groups."""
import contextlib
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pkgs_lib import cli, completion
from pkgs_lib.grammar import COMMANDS


class CompletionTypes(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='pkgs completion types ')
        self.addCleanup(temporary.cleanup)
        self.home=Path(temporary.name)
        self.env={key:value for key,value in os.environ.items()
                  if key in ('PATH','PREFIX','LD_PRELOAD','SYSTEMROOT','SystemRoot')}
        self.env.update(HOME=str(self.home),PKGS_FUZZY_TAB='0',
                        XDG_CONFIG_HOME=str(self.home/'config'),XDG_STATE_HOME=str(self.home/'state'),
                        XDG_DATA_HOME=str(self.home/'data'),XDG_CACHE_HOME=str(self.home/'cache'))
        self.environment=patch.dict(os.environ,self.env,clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)

    def test_every_command_and_alias_options_keep_normal_records(self):
        cases=[([''],'command'),(['--'],'option'),(['--scope',''],'value'),
               (['--color',''],'value'),(['completion',''],'value'),
               (['completion','zsh',''],'command'),(['cache',''],'command')]
        cases += [([name,'--'],'option') for name in COMMANDS]
        for words,role in cases:
            with self.subTest(words=words):
                plain=completion.complete(words,{})
                typed=completion.complete(words,{},display_types=True)
                self.assertTrue(typed)
                self.assertEqual([row[:2] for row in typed],plain)
                self.assertTrue(all(row[2]==role for row in typed),typed)
                self.assertNotIn('\x1b',str(typed))
        self.assertEqual({row[0] for row in completion.complete([''],{},display_types=True)},set(COMMANDS))
        self.assertEqual(list(self.home.iterdir()),[])

    def test_private_cli_opt_in_and_default_bytes(self):
        with patch.object(cli,'config',return_value={}):
            for typed in (False,True):
                stream=io.StringIO()
                argv=['__complete',*(['--display-types'] if typed else []),'--','--color','']
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(cli.main(argv),0)
                rows=stream.getvalue().splitlines()
                self.assertEqual(rows,[name+'\tcolor mode'+('\tvalue' if typed else '')
                                       for name in ('auto','always','never')])

    @unittest.skipUnless(shutil.which('zsh'),'Zsh unavailable')
    def test_zsh_groups_with_literal_empty_descriptions(self):
        # The provider fixture only replays records; no package manager is run.
        executable=self.home/'pkgs'
        executable.write_text('#!'+shutil.which('sh')+'\ncat "$HOME/records"\n')
        executable.chmod(0o700)
        env=dict(self.env,PATH=str(self.home)+os.pathsep+self.env['PATH'])
        for role in ('command','option','value'):
            (self.home/'records').write_text('literal: name\t\t'+role+'\nsecond\tdescription\t'+role+'\n')
            code=r'''
compadd() {
  local group
  while (( $# )); do
    case $1 in
      -J) group=$2; shift 2 ;;
      -X|-d) shift 2 ;;
      -U) shift ;;
      --) shift; break ;;
    esac
  done
  for value in "$@"; do print -r -- "$curtag/$group:$value"; done
}
_pkgs() { source SCRIPT; }
words=(pkgs ''); CURRENT=2; _pkgs
'''.replace('SCRIPT',shlex.quote(str(ROOT/'completions/pkgs.zsh')))
            result=subprocess.run([shutil.which('zsh'),'-dfc',code],env=env,cwd=self.home,
                                  text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.splitlines(),[role+'s/'+role+'s:'+name
                                                          for name in ('literal: name','second')])


if __name__=='__main__':
    unittest.main()
