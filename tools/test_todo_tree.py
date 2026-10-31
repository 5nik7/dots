#!/usr/bin/env python3
"""Tree views preserve goal data, ordering and read-only ancestor context."""
import io
import json
import os
from unittest.mock import patch
import unittest
import test_todo as fixtures
from todo_tree import tree,filtered
from todo_core import Goals,scope

class Tree(unittest.TestCase):
    def setUp(self):fixtures.Todo.setUp(self)
    cli=fixtures.Todo.cli
    add=fixtures.Todo.add

    def test_cli_tree_context_matches_and_exact_data(self):
        parent=self.add('Parent',priority='low',alias='parent')
        child=self.add('Child needle',parent=parent['id'],priority='high')
        other=self.add('Other',priority='normal')
        tree_output=self.cli('list','--query','needle').stdout
        self.assertIn('1',tree_output);self.assertIn('[context]',tree_output)
        self.assertIn('Parent',tree_output);self.assertIn('Child needle',tree_output)
        self.assertLess(tree_output.index('Parent'),tree_output.index('Child needle'))
        self.assertNotIn('Parent',self.cli('list','--query','needle','--list-type','regular').stdout)
        json_tree=self.cli('list','--query','needle','--list-type','tree','--json').stdout
        self.assertEqual(json_tree,self.cli('list','--query','needle','--list-type','regular','--json').stdout)
        self.assertEqual([g['id'] for g in json.loads(json_tree)['goals']],[child['id']])
        self.assertEqual(self.cli('list','--markdown','--list-type','regular').stdout,self.cli('list','--markdown','--list-type','tree').stdout)
        view=tree([child,other],[parent,child,other])
        self.assertEqual([(g['title'],depth,context) for g,depth,context in view],[('Other',0,False),('Parent',0,True),('Child needle',1,False)])

    def test_fuzzy_filter_and_parent_non_actionability(self):
        parent=self.add('Parent');child=self.add('Needle child',parent=parent['id'])
        snapshot=dict(schema=1,goals=[parent,child],eligible=[1],search=['Parent','Needle child'],
                      labels=['PARENT','CHILD'],context=['MUTED PARENT','MUTED CHILD'],indent=2)
        payload,matches,indices=filtered(snapshot,'nch')
        self.assertEqual(matches,{1});self.assertEqual(indices,[0,1])
        self.assertIn(b'1 matching goals',payload);self.assertIn(b'0\tMUTED PARENT\0',payload)
        from todo_menu import browse
        from todo_commands import parser
        from interaction import SelectionEvent
        args=parser().parse_args(['browse'])
        ancestor=dict(parent,_todo_context=True)
        def fake_pick(store,goals,frame,context):
            frame['_goals']=[ancestor]
            if not frame.get('notice'):raise SelectionEvent('plan',0)
            return None
        with patch('todo_menu.pick',side_effect=fake_pick),patch('todo_menu.apply') as mutate,patch('todo_plan.launch') as launch:
            self.assertEqual(browse(scope(),args),0)
            mutate.assert_not_called();launch.assert_not_called()

if __name__=='__main__':unittest.main()
