#!/usr/bin/env python3
"""Audit every first-party route from live static metadata in an owned checkout.

No command actions, plugin backends, user configuration or package managers run.
The private typed projection must round-trip to the ordinary literal protocol.
"""
import json
import os
import shlex
import shutil
import subprocess
import unittest

import test_completion_colors as fixtures
from command_metadata import BUILTINS, catalog, read


@unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'requires a native POSIX Bash fixture; Windows bash.exe may be WSL interop')
class CompletionCatalog(unittest.TestCase):
    setUp = fixtures.CompletionColors.setUp

    def test_all_routes_options_and_static_choices(self):
        # Match an initialized shell's pre-resolved command roots. Profiles in
        # this fixture have no extra bins; do not parse the same profile for
        # every one of the catalog's queries.
        self.env.update(DOTS_PROFILE_CHECKOUT=str(self.root), DOTS_PROFILE_BIN_PATHS='')
        rows = catalog([self.root/'bin'])
        for name in BUILTINS:
            rows[name] = read(self.root/'lib/dots/metadata'/f'{name}.meta')
        bundled = json.loads((self.root/'lib/dots/metadata/bundled-apps.json').read_text())
        self.assertFalse(set(bundled)-set(rows), 'Bundled routes need dispatcher metadata')
        # Replace action bodies with sentinels while retaining authoritative
        # headers. Completion may read metadata, never execute these actions.
        for source in (self.root/'bin').glob('dots-*'):
            lines = source.read_text().splitlines(keepends=True)
            header = []
            for line in lines:
                if line.strip() and not line.startswith('#'): break
                header.append(line)
            source.write_text(''.join(header)+'\necho EXECUTED_COMMAND >&2\nexit 97\n')
        prefixes = {()}
        for stem in rows:
            route = tuple(stem.split('-'))
            prefixes.update(route[:i] for i in range(1, len(route)+1))
        cases = {}
        for route in sorted(prefixes):
            children = {key[len(route)] for stem, row in rows.items()
                        if not row['hidden'] and len(key := tuple(stem.split('-'))) > len(route)
                        and key[:len(route)] == route}
            cases[(*route, '')] = ('children', children)
            cases[(*route, '--')] = ('options', set())
        for stem, row in rows.items():
            route = tuple(stem.split('-'))
            for long, short, kind, _ in row['option']:
                if kind.startswith('choice:'):
                    # init's installation options are gated by explicit setup;
                    # querying __complete never invokes that action.
                    context = (*route, '--setup') if stem == 'init' and long != '--bootstrap' else route
                    cases[(*context, long, '')] = ('values', set(kind[7:].split(',')))
            # Later positionals may require data-dependent earlier arguments;
            # the first finite argument is independently observable here.
            for position, kind, _ in row['argument']:
                if position == '1' and kind.startswith('choice:'):
                    children = cases[(*route, '')][1]
                    expected = {value: b'value' for value in kind[7:].split(',')}
                    expected.update({value: b'command' for value in children})
                    cases[(*route, '')] = ('mixed', expected)
        cases[('init','--setup','--')] = ('options', set())
        selected = tuple(shlex.split(os.environ.get('DOTS_TEST_COMPLETION_PREFIX','')))
        if selected:
            cases = {tail: expected for tail, expected in cases.items() if tail[:len(selected)] == selected}
            self.assertTrue(cases, 'No completion contexts match the requested prefix')
            print('\nFiltered completion prefix: '+shlex.join(selected),flush=True)
        total = 0
        for tail, (kind, expected) in cases.items():
            with self.subTest(command=('dots', *tail)):
                words = ['dots', *tail]
                base = [str(self.root/'bin/dots'), '__complete', 'zsh', str(len(words)-1)]
                results = []
                for extra in ([], ['--display-types']):
                    result = subprocess.run([*base, *extra, '--', *words], env=self.env,
                                            cwd=self.home, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn(b'EXECUTED_COMMAND', result.stderr)
                    self.assertNotIn(b'\x1b', result.stdout)
                    results.append(result.stdout)
                records = [line.split(b'\t') for line in results[1].splitlines()]
                self.assertEqual(b''.join(b'\t'.join(row[:3])+b'\n' for row in records), results[0])
                candidates = {}
                for record in records:
                    if record[0] == b'candidate':
                        self.assertEqual(len(record), 4, record)
                        self.assertIn(record[3], (b'command', b'option', b'value'), record)
                        candidates[record[1].decode()] = record[3]
                    else:
                        self.assertIn(record[0], (b'file', b'directory'), record)
                        self.assertEqual(len(record), 3, record)
                if kind == 'options':
                    self.assertTrue(all(role == b'option' for role in candidates.values()), candidates)
                else:
                    for value in expected:
                        self.assertIn(value, candidates)
                        role = expected[value] if kind == 'mixed' else b'command' if kind == 'children' else b'value'
                        self.assertEqual(candidates[value], role)
                total += 1
                if total % 100 == 0:
                    print(f'\nChecked {total}/{len(cases)} contexts',flush=True)
        print(f'\nCatalog: {len(rows)} routes, {len(prefixes)} prefixes; checked {total} completion contexts'
              + (' (filtered).' if selected else ' (complete).'), flush=True)


if __name__ == '__main__':
    unittest.main()
