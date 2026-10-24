#!/usr/bin/env python3
"""Documentation checks use only disposable parent-repository fixtures."""
from pathlib import Path
import tempfile
import unittest
from verify_docs import check_links


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots docs ü ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'README.md').write_text('# Fixture\n', encoding='utf-8')
        (self.root / 'AGENTS.md').write_text('# Guide\n', encoding='utf-8')
        (self.root / 'docs').mkdir()

    def readme(self, text):
        (self.root / 'README.md').write_text(text, encoding='utf-8')

    def test_relative_encoded_paths_and_anchor_only_links(self):
        (self.root / 'docs/a ü.md').write_text('# Heading\n', encoding='utf-8')
        self.readme('[file](docs/a%20%C3%BC.md#heading) [self](#fixture)')
        self.assertEqual(check_links(self.root), (1, 3))

    def test_missing_target_is_an_error(self):
        self.readme('[missing](docs/missing.md)')
        with self.assertRaisesRegex(RuntimeError, 'README.md -> docs/missing.md'):
            check_links(self.root)

    def test_uninitialized_submodule_is_not_a_document_target(self):
        (self.root / 'optional').mkdir()
        self.readme('[missing](optional/docs/usage.md)')
        with self.assertRaises(RuntimeError):
            check_links(self.root)
        self.readme('[public](https://example.invalid/repo/blob/revision/docs/usage.md)')
        self.assertEqual(check_links(self.root), (0, 2))
        self.assertFalse(list((self.root / 'optional').iterdir()))

    def test_native_and_link_text_checkouts(self):
        target = self.root / 'docs/usage.md'
        target.write_text('# Usage\n', encoding='utf-8')
        alias = self.root / 'alias'
        self.readme('[usage](alias)')
        try:
            alias.symlink_to('docs/usage.md')
        except OSError:
            pass  # Link-text behavior is still testable without link privilege.
        else:
            self.assertEqual(check_links(self.root), (1, 3))
            alias.unlink()
        alias.write_text('docs/usage.md', encoding='utf-8')
        self.assertEqual(check_links(self.root), (1, 3))


if __name__ == '__main__':
    unittest.main()
