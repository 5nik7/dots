"""Regression for absolute checkout links escaping disposable fixtures."""
from pathlib import Path
import tempfile
import unittest

from public_fixture import copy_public_tree


class PublicFixtureTests(unittest.TestCase):
    def test_internal_absolute_links_are_rebased(self):
        with tempfile.TemporaryDirectory(prefix='dots-fixture-') as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'fixture'
            source.mkdir()
            (source / 'palette').write_text('original')
            (source / 'absolute').symlink_to(source / 'palette')
            (source / 'relative').symlink_to('palette')
            copy_public_tree(source, target, repo=source, fixture=target)
            for name in ('absolute', 'relative'):
                self.assertEqual((target / name).resolve(), target / 'palette')
            (target / 'absolute').write_text('fixture mutation')
            self.assertEqual((source / 'palette').read_text(), 'original')

    def test_external_link_is_rejected_before_copying(self):
        with tempfile.TemporaryDirectory(prefix='dots-fixture-') as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'fixture'
            source.mkdir()
            (source / 'escape').symlink_to(root / 'outside')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                copy_public_tree(source, target, repo=source, fixture=target)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
