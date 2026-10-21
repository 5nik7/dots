#!/usr/bin/env python3
"""Palette surgery and journaled application, with all paths owned by fixtures."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'lib/dots/themes'), str(ROOT/'lib/dots/files'), str(ROOT/'lib/dots')]
import starship
import transactions


class Palette(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots-starship-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root/'home space ü -dash';self.home.mkdir()
        self.config = self.home/'config';self.config.mkdir()
        self.state = self.home/'state/dots'
        self.generation = self.home/'generation';self.generation.mkdir()
        self.active = self.home/'active.toml'
        self.storage = self.home/'blastoff';(self.storage/'themes').mkdir(parents=True)
        self.saved = self.storage/'themes/dots.toml'
        self.env = dict(HOME=str(self.home), XDG_CONFIG_HOME=str(self.config),
                        XDG_STATE_HOME=str(self.home/'state'), XDG_CACHE_HOME=str(self.home/'cache'),
                        XDG_DATA_HOME=str(self.home/'data'), XDG_RUNTIME_DIR=str(self.home/'runtime'),
                        TMPDIR=str(self.root), STARSHIP_CONFIG=str(self.active), BLASTOFF_HOME=str(self.storage),
                        STARSHIP_CACHE=str(self.home/'cache/starship'),
                        GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1')
        self.patcher=patch.dict(os.environ,self.env);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.original=b'palette="dots"\n# unchanged header\n[palettes.dots]\nblue="#123456"\ncustom="red"\n\n[directory]\nstyle="blue"\ntruncation_length=7\n'
        self.active.write_bytes(self.original);self.saved.write_bytes(self.original)
        self.generation.joinpath('blastoff.toml').write_text('palette="dots"\n[palettes.dots]\nblue="#abcdef"\ngit_branch="#112233"\n')

    def test_home_default_link_ignores_xdg_and_preserves_target(self):
        os.environ.pop('STARSHIP_CONFIG', None)
        default = self.home/'.config/starship.toml'
        default.parent.mkdir()
        default.symlink_to(self.active)
        guards = {}
        active, _, _ = starship.paths(guards)
        self.assertEqual(active, self.active)
        self.assertIn(str(default), guards)
        self.assertEqual(default.read_bytes(), self.original)
        self.assertFalse((self.config/'starship.toml').exists())

    def test_surgery_multiline_quotes_arrays_and_bytes(self):
        prefix='\ufeffpalette="dots"\nformat="""\n[palettes.dots]\nnot a real table\n"""\ntext=\'\'\'\n[another.table]\n\'\'\'\n# prefix\n'
        suffix='  [directory]\nstyle="blue" # comment\n[[battery.display]]\nthreshold=10\nstyle="red"\n[palettes.other]\nblue="green"\n'
        for newline in ('\n','\r\n'):
            data=(prefix+'["palettes" . "dots"] # quoted\nblue="#123456"\ncustom="red"\n'+suffix).replace('\n',newline).encode()
            out=starship.update_palette(data, {'blue':'#abcdef'})
            self.assertTrue(out.startswith(prefix.replace('\n',newline).encode()))
            self.assertTrue(out.endswith(suffix.replace('\n',newline).encode()))
            doc=tomllib.loads(out.decode('utf-8-sig'))
            self.assertEqual(doc['palettes']['dots'],dict(blue='#abcdef',custom='red'))
            self.assertEqual(out,starship.update_palette(out,{'blue':'#abcdef'}))

    def test_skip_append_and_unsupported_toml(self):
        other=self.original.replace(b'palette="dots"',b'palette="other"')
        self.assertEqual(starship.update_palette(other,{'blue':'#abcdef'}),other)
        appended=starship.update_palette(b'palette="dots"\n[directory]\nstyle="blue"',{'blue':'#abcdef'})
        self.assertEqual(tomllib.loads(appended.decode())['directory'],{'style':'blue'})
        for data in (b'palette="dots"\n[broken',b'palette="dots"\npalettes={dots={blue="red"}}',
                     b'palette="dots"\n[palettes.dots]\nblue=2', b'palette="dots"\npalettes=2'):
            with self.assertRaises(ValueError):starship.update_palette(data,{'blue':'#abcdef'})

    def test_apply_idempotent_preserves_edits_and_other_theme(self):
        self.saved.write_bytes(self.original.replace(b'truncation_length=7',b'truncation_length=12'))
        result=starship.apply(self.config,self.state,self.generation)
        self.assertIn('transaction',result)
        self.assertEqual(tomllib.loads(self.saved.read_text())['directory']['truncation_length'],12)
        mtimes=[p.stat().st_mtime_ns for p in (self.active,self.saved)]
        self.assertNotIn('transaction',starship.apply(self.config,self.state,self.generation))
        self.assertEqual(mtimes,[p.stat().st_mtime_ns for p in (self.active,self.saved)])
        other=self.original.replace(b'palette="dots"',b'palette="other"');self.active.write_bytes(other)
        self.saved.write_bytes(self.original)
        starship.apply(self.config,self.state,self.generation)
        self.assertEqual(self.active.read_bytes(),other)
        self.assertIn('#abcdef',self.saved.read_text())

    def test_symlink_targets_and_storage_alias(self):
        alias=self.home/'alias.toml';alias.symlink_to(self.active)
        storage_alias=self.home/'storage-alias';storage_alias.symlink_to(self.storage,target_is_directory=True)
        with patch.dict(os.environ,STARSHIP_CONFIG=str(alias),BLASTOFF_HOME=str(storage_alias)):
            starship.apply(self.config,self.state,self.generation)
        self.assertTrue(alias.is_symlink() and storage_alias.is_symlink())
        self.assertIn('#abcdef',self.active.read_text())
        alias.unlink();alias.symlink_to('missing.toml')
        with patch.dict(os.environ,STARSHIP_CONFIG=str(alias)):
            starship.apply(self.config,self.state,self.generation)
        self.assertFalse((self.home/'missing.toml').exists())

    def test_link_retarget_is_refused_before_any_write(self):
        alias = self.home/'alias.toml';alias.symlink_to(self.active)
        other = self.home/'other.toml';other.write_bytes(self.original)
        original_apply = transactions.Store.apply
        def retarget(store,*args,**kwargs):
            alias.unlink();alias.symlink_to(other)
            return original_apply(store,*args,**kwargs)
        with patch.dict(os.environ,STARSHIP_CONFIG=str(alias)), patch.object(transactions.Store,'apply',retarget):
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                starship.apply(self.config,self.state,self.generation)
        for path in (self.active,self.saved,other):self.assertEqual(path.read_bytes(),self.original)

    def test_locks_malformed_and_special_files(self):
        lock=self.storage/'.operation.lock';lock.mkdir()
        with self.assertRaisesRegex(ValueError,'lock'):starship.apply(self.config,self.state,self.generation)
        lock.rmdir();self.saved.write_text('[broken')
        with self.assertRaises(ValueError):starship.apply(self.config,self.state,self.generation)
        self.assertEqual(self.active.read_bytes(),self.original)
        self.saved.unlink();os.mkfifo(self.saved)
        with self.assertRaises(ValueError):starship.apply(self.config,self.state,self.generation)
        self.assertEqual(self.active.read_bytes(),self.original)

    def test_concurrent_edit_and_rollback(self):
        original_apply=transactions.Store.apply
        def edit(store,*args,**kwargs):
            self.active.write_bytes(self.original+b'# external edit\n')
            return original_apply(store,*args,**kwargs)
        with patch.object(transactions.Store,'apply',edit):
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                starship.apply(self.config,self.state,self.generation)
        self.assertEqual(self.saved.read_bytes(),self.original)
        self.active.write_bytes(self.original)
        original_replace=os.rename
        failed = False
        def fail(source,target,*args,**kwargs):
            nonlocal failed
            if not failed and str(target)==str(self.saved) and '.dots-new-' in str(source):
                failed = True
                raise OSError('fixture failure')
            return original_replace(source,target,*args,**kwargs)
        with patch.object(os,'rename',fail):
            with self.assertRaises(OSError):starship.apply(self.config,self.state,self.generation)
        self.assertEqual(self.active.read_bytes(),self.original)
        self.assertEqual(self.saved.read_bytes(),self.original)

    @unittest.skipUnless(shutil.which('starship'),'native Starship unavailable')
    def test_saved_theme_coverage_and_native_render(self):
        source=ROOT/'config/blastoff/themes/dots.toml'
        self.active.write_bytes(source.read_bytes())
        defaults=tomllib.loads(subprocess.check_output(['starship','print-config','--default'],text=True,cwd=self.home,env=dict(os.environ,STARSHIP_CONFIG=os.devnull)))
        supported=subprocess.check_output(['starship','module','--list'],text=True,cwd=self.home).splitlines()
        configured=tomllib.loads(self.active.read_text())
        for name,values in defaults.items():
            if not isinstance(values,dict) or name not in supported:continue
            for key,value in values.items():
                if isinstance(value,str) and (key=='style' or key.endswith('_style') or key in ('style_user','style_root')):
                    self.assertIn(key,configured.get(name,{}),(name,key))
                elif key=='display' and isinstance(value,list) and value and 'style' in value[0]:
                    self.assertEqual(len(configured[name][key]),len(value))
        colors=configured['palettes']['dots']
        import re
        for token in re.findall(r'\b(?:fg|bg):([a-z_][a-z_0-9]*)',self.active.read_text()):
            self.assertIn(token,colors)
        for module in ('character','directory','status'):
            result=subprocess.run(['starship','module',module],cwd=self.home,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('WARN',result.stderr)
            self.assertNotIn('Error',result.stderr)
        result=subprocess.run(['starship','module','character'],cwd=self.home,text=True,capture_output=True)
        self.assertIn('\x1b[',result.stdout)
        repo=self.home/'git-fixture';repo.mkdir()
        subprocess.run(['git','init','-b','fixture'],cwd=repo,check=True,capture_output=True)
        (repo/'new').write_text('fixture')
        result=subprocess.run(['starship','prompt'],cwd=repo,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('?1',result.stdout)
        self.assertNotIn('WARN',result.stderr)


if __name__=='__main__':unittest.main()
