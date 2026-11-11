"""Saved-theme link behavior through the actual shared application frontend."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class LinkedThemes(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='blastoff-links-');self.addCleanup(temp.cleanup)
        self.home=Path(temp.name);self.storage=self.home/'blastoff';self.themes=self.storage/'themes';self.themes.mkdir(parents=True)
        self.active=self.home/'starship.toml'
        self.env=dict(os.environ,HOME=str(self.home),USERPROFILE=str(self.home),DOTS=str(ROOT),
            BLASTOFF_HOME=str(self.storage),STARSHIP_CONFIG=str(self.active),XDG_STATE_HOME=str(self.home/'state'),
            XDG_CONFIG_HOME=str(self.home/'config'),XDG_DATA_HOME=str(self.home/'data'),XDG_CACHE_HOME=str(self.home/'cache'))
        for name,color in [('one','red'),('two','blue')]: (self.themes/(name+'.toml')).write_text('format="'+color+'"\n')
    def cli(self,*args,code=0):
        p=subprocess.run([sys.executable,'-B',str(ROOT/'plugins/blastoff/lib/blastoff.py'),*args,'--json'],
            env=self.env,cwd=self.home,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,code,p.stdout+p.stderr)
        return json.loads(p.stdout) if p.stdout else None
    def test_apply_repeat_switch_retains_the_previous_theme(self):
        self.active.write_text('format="old"\n')
        result=self.cli('theme','apply','one');self.assertTrue(result['backup'])
        self.assertEqual(self.active.resolve(),self.themes/'one.toml')
        self.assertIsNone(self.cli('theme','apply','one')['backup'])
        self.assertTrue(self.cli('theme','apply','one','--dry-run')['dry_run'])
        self.assertIsNone(self.cli('theme','save')['backup'])
        self.cli('theme','apply','two')
        self.assertEqual(self.active.resolve(),self.themes/'two.toml')
        self.assertEqual((self.themes/'one.toml').read_text(),'format="red"\n')
        self.cli('theme','delete','two','--force',code=1)
        self.assertTrue(self.active.exists())
    def test_linked_module_edit_updates_saved_source(self):
        self.cli('theme','apply','one')
        modules=self.storage/'modules';modules.mkdir();(modules/'test.toml').write_text('[character]\nsuccess_symbol="ok"\n')
        self.cli('module','load','test')
        self.assertTrue(self.active.is_symlink())
        self.assertIn('success_symbol',(self.themes/'one.toml').read_text())
        records=json.loads((self.home/'state/dots/bak/catalog.json').read_text())['entries']
        self.assertTrue(any(r.get('blastoff',{}).get('kind')=='config' for r in records.values()))
    def test_dry_run_is_inert(self):
        before=set(self.home.rglob('*'))
        self.cli('theme','apply','one','--dry-run')
        self.assertEqual(set(self.home.rglob('*')),before)

    @unittest.skipIf(os.name=='nt', 'POSIX executable fixture; native preset acceptance separate')
    def test_presets_materialize_without_local_name_collision(self):
        tools=self.home/'tools';tools.mkdir()
        starship=tools/'starship'
        program='import sys\nprint("one" if "--list" in sys.argv else '+repr('format="preset"')+')\n'
        starship.write_text('#!'+sys.executable+'\n'+program)
        starship.chmod(0o700)
        self.env['PATH']=str(tools)+os.pathsep+self.env.get('PATH','')
        self.cli('preset','apply','one')
        target=self.active.resolve()
        self.assertTrue(target.name.startswith('preset-one-'))
        self.assertEqual((self.themes/'one.toml').read_text(),'format="red"\n')
        self.cli('preset','apply','one')
        self.assertEqual(self.active.resolve(),target)

if __name__=='__main__':unittest.main()
