#!/usr/bin/env python3
"""Typed config and exact reads in disposable profile/state roots."""
import json
import os
import shutil
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from config_values import Controls, parts, name, current
from config_cli import ControlPlan
from profile_config import context, keys
from transactions import Store

class Values(fixtures.ProfileConfig):
    def setUp(self):
        super().setUp()
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        self.environ=patch.dict(os.environ,self.env,clear=True);self.environ.start();self.addCleanup(self.environ.stop)
        current.cache_clear();self.addCleanup(current.cache_clear)

    def test_literals_types_null_and_data(self):
        key='apps.nvim.highlights["@variable.member"].fg'
        self.assertEqual(name(parts(key)),key)
        self.assertIn('formatting.apps.todo.list_type',keys(self.root))
        self.assertIn('colors.todo.field.status.value.fg',keys(self.root))
        self.assertEqual(self.run_config('get','colors.todo.field.status.value.fg').stdout,'null\n')
        self.assertEqual(self.run_config('get',key).stdout,'null\n')
        self.assertIsNone(json.loads(self.run_config('get',key,'--json').stdout)['value'])
        self.run_config('get','apps.nvim.typo',code=1)
        self.run_config('set',key,'#123456','--no-refresh')
        self.assertEqual(self.run_config('get',key,native=True).stdout,'#123456\n')
        self.run_config('set','apps.nvim.options.wrap','false','--no-refresh')
        self.assertEqual(self.run_config('get','apps.nvim.options.wrap').stdout,'false\n')
        self.run_config('set','formatting.apps.todo.indent','0','--no-refresh')
        self.assertEqual(self.run_config('get','formatting.apps.todo.indent').stdout,'0\n')
        self.run_config('set','formatting.apps.todo.list_type','invalid','--no-refresh',code=1)
        self.run_config('set','apps.nvim.options.wrap','null','--json-value','--no-refresh')
        self.assertEqual(self.run_config('get','apps.nvim.options.wrap').stdout,'true\n')
        self.assertEqual(self.run_config('get','colors.apps.tmux.status.warning.fg').stdout,'warning\n')
        self.assertEqual(self.run_config('get','colors.apps.cli.ui.heading.bg').stdout,'null\n')
        self.run_config('get','colors.not_a_role.fg',code=1)
        for malformed in ('apps.nvim.highlights["x"]junk','apps.nvim.highlights[1]','apps..nvim'):
            self.run_config('get',malformed,code=1)

    def test_guards_undo_and_popup(self):
        from config_menu import Inventory,Draft
        original=self.path.read_bytes()
        row=Inventory(self.root,self.platform).find('formatting.apps.todo.list_type')
        draft=Draft(Inventory(self.root,self.platform),row).prepare('regular')
        self.assertEqual(draft.proposed,'regular')
        result=draft.plan.apply('set')
        self.assertEqual(Controls(self.root).resolve(row.key)['value'],'regular')
        store=Store(self.home/'state/dots');ops,guards,catalogs=store.inverse(result['id'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual(json.loads(self.path.read_bytes()),json.loads(original))
        plan=ControlPlan(self.root,context(self.root));plan.edit('formatting.apps.todo.indent','3')
        self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaises(ValueError):plan.apply('set')

if __name__=='__main__':unittest.main()
