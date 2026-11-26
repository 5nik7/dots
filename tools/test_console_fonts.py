"""Exercise Console font journals with an in-memory substitute for HKCU."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots/files'))
import console_font_registry as registry
from transactions import Store


class ConsoleTests(unittest.TestCase):
    def test_rollback_and_undo_restore_each_face(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / 'state')
            values = {'PowerShell': 'Other Font'}
            def write(name, value):
                if value is None:
                    values.pop(name, None)
                else:
                    values[name] = value

            ops = [dict(path=str(root / filename), data=dict(schema=1),
                        console_face=dict(name=name, before=values.get(name), after='Fixture Mono'))
                   for name, filename in [('', 'default.json'), ('PowerShell', 'profile.json')]]
            guards = {op['path']: None for op in ops}
            with patch.object(registry, 'read', side_effect=values.get), patch.object(registry, 'write', side_effect=write):
                result = store.apply('fonts-set', ops, guards, retain=True)
                self.assertEqual(values, {'': 'Fixture Mono', 'PowerShell': 'Fixture Mono'})
                values['PowerShell'] = 'Manual'
                with self.assertRaises(ValueError):
                    store.inverse(result['id'])
                values['PowerShell'] = 'Fixture Mono'
                inverse, inputs, catalogs = store.inverse(result['id'])
                store.apply('undo', inverse, inputs, retain=True, catalogs=catalogs)
                self.assertEqual(values, {'PowerShell': 'Other Font'})
                def fail(name, value):
                    write(name, value)
                    if name == 'PowerShell' and value == 'Fixture Mono':
                        raise OSError('interrupted after writing profile')
                with patch.object(registry, 'write', side_effect=fail), self.assertRaises(OSError):
                    store.apply('fonts-set', ops, guards, retain=True)
                self.assertEqual(values, {'PowerShell': 'Other Font'})
                self.assertFalse(any(Path(path).exists() for path in guards))

    def test_only_existing_console_profile_names(self):
        for name in ('Console\\Other', '%%Startup', 'name\x01'):
            with self.assertRaises(ValueError):
                registry.key_path(name)


if __name__ == '__main__':
    unittest.main()
