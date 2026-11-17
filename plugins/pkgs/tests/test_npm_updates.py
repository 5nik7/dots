"""Automatic global npm upgrades avoid reinstalls; explicit recipes keep control."""
import json
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib import outdated, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error, Package


class NpmUpdates(unittest.TestCase):
    setUp = fixtures.Workflows.setUp

    def rows(self, *names):
        return [(Package(name, '1.0.0'), 'global', '') for name in names]

    def test_only_native_candidates_are_installed_and_current_is_empty(self):
        rows = self.rows('current', 'newer', 'held')
        rows += [(Package('source', '1.0.0'), 'global', 'source install')]
        cfg = dict(self.cfg, policies={'npm': {'skip': ['held']}})
        for candidates, expected in (([{'name': 'newer'}], ['newer']), ([], [])):
            with self.subTest(candidates=candidates), patch.object(workflows.scopes, 'inventory', return_value=rows), \
                 patch.object(outdated, 'candidates', return_value=candidates) as query:
                item = workflows.plan(Backend('npm', True), 'upgrade', [], cfg)
            self.assertEqual([p.name for p in query.call_args.args[1]], ['current', 'newer'])
            self.assertEqual(item.names, expected)
            self.assertEqual(item.commands, [['npm', 'install', '--global', '--', *expected]] if expected else [])
            self.assertEqual({p['package'] for p in item.skipped}, {'source', 'held'})

    def test_explicit_project_and_install_paths_do_not_filter(self):
        for action, names, global_scope in (('upgrade', ['current'], True), ('upgrade', [], False),
                                             ('install', ['current'], True)):
            with self.subTest(action=action, names=names, global_scope=global_scope), \
                 patch.object(workflows.scopes, 'inventory', return_value=self.rows('current')), \
                 patch.object(outdated, 'candidates') as query:
                item = workflows.plan(Backend('npm', global_scope), action, names, self.cfg)
            query.assert_not_called()
            self.assertTrue(item.commands)

    def test_manager_recipes_bypass_filtering(self):
        for recipe in ({'flags': ['--force']}, {'before': [['fixture', 'before']]},
                       {'after': [['fixture', 'after']]}, {'replace': [['fixture', '{packages}']]}):
            cfg = dict(self.cfg, policies={'npm': {'upgrade': recipe}})
            with self.subTest(recipe=recipe), patch.object(workflows.scopes, 'inventory', return_value=self.rows('current')), \
                 patch.object(outdated, 'candidates') as query:
                item = workflows.plan(Backend('npm', True), 'upgrade', [], cfg)
            query.assert_not_called()
            self.assertEqual(item.names, ['current'])
            self.assertTrue(item.commands)

    def test_package_recipes_are_not_queried_or_filtered(self):
        rules = {'forced': {'upgrade': {'flags': ['--force']}},
                 'hooked': {'upgrade': {'before': [['fixture', 'before']], 'after': [['fixture', 'after']]}},
                 'replaced': {'upgrade': {'replace': [['fixture', '{package}']]}}}
        cfg = dict(self.cfg, policies={'npm': {'packages': rules}})
        for ordinary in ([], ['current']):
            with self.subTest(ordinary=ordinary), \
                 patch.object(workflows.scopes, 'inventory', return_value=self.rows(*ordinary, *rules)), \
                 patch.object(outdated, 'candidates', return_value=[]) as query:
                item = workflows.plan(Backend('npm', True), 'upgrade', [], cfg)
            self.assertEqual(query.call_count, bool(ordinary))
            if ordinary: self.assertEqual([p.name for p in query.call_args.args[1]], ordinary)
            self.assertEqual(item.names, list(rules))
            self.assertEqual(item.commands, [['npm', 'install', '--global', '--force', '--', 'forced'],
                                            ['fixture', 'before'], ['npm', 'install', '--global', '--', 'hooked'],
                                            ['fixture', 'after'], ['fixture', 'replaced']])

    def test_failed_query_cannot_fall_back_to_reinstallation(self):
        with patch.object(workflows.scopes, 'inventory', return_value=self.rows('current')), \
             patch.object(outdated, 'candidates', side_effect=Error('fixture query failed')), \
             patch.object(Backend, 'transaction') as transaction:
            with self.assertRaisesRegex(Error, 'fixture query failed'):
                workflows.plan(Backend('npm', True), 'upgrade', [], self.cfg)
        transaction.assert_not_called()

    def test_native_query_targets_wanted_version_and_rejects_invalid_metadata(self):
        backend = Backend('npm', True); backend.operation_env = {'fixture': 'environment'}
        data = {'tool': {'current': '1.0.0', 'wanted': '1.1.0', 'latest': '2.0.0'}}
        with patch.object(outdated, 'fetch', return_value=json.dumps(data)) as fetch:
            self.assertEqual(outdated.candidates(backend, [Package('tool', '1.0.0')]),
                             [{'name': 'tool', 'current': '1.0.0', 'candidate': '1.1.0'}])
        fetch.assert_called_once_with(['npm', 'outdated', '--json', '--global', '--', 'tool'],
                                      allowed=(0, 1), env=backend.operation_env)
        for value in ([], {'error': {}}, {'tool': None}, {'tool': {}}, {'tool': {'current': '1.0.0', 'wanted': 7}}):
            with self.subTest(value=value), patch.object(outdated, 'fetch', return_value=json.dumps(value)):
                with self.assertRaises(Error): outdated.candidates(backend, [Package('tool', '1.0.0')])


if __name__ == '__main__': unittest.main()
