#!/usr/bin/env python3
import json
from pathlib import Path
import tempfile
import unittest

from audit_config import scan


class AuditTests(unittest.TestCase):
    def test_static_bounded_deterministic_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'repo ü'; root.mkdir()
            for name in ('lib','profiles/termux','profiles/linux','config/private','tools','default','.dots'):
                (root/name).mkdir(parents=True,exist_ok=True)
            (root/'lib/render.py').write_text('raise RuntimeError("must not execute")\nfg = "#aabbcc"\nicon = "󰄬"\nindent = 2\npassword = "#123456"\n')
            (root/'tools/test_example.py').write_text('fg = "#112233"')
            (root/'profiles/termux/colors.toml').write_text('[ui.heading]\nfg="cyan"\n')
            (root/'profiles/linux/colors.toml').write_text('[ui.heading]\nfg="blue"\n')
            (root/'config/private/options.py').write_text('fg="#000000"')
            (root/'.dots/sources.json').write_text(json.dumps({'sources':[{'path':'config/private','excluded':True}]}))
            (root/'lib/outside').symlink_to(Path(temp),target_is_directory=True)
            before={str(p):p.stat().st_mtime_ns for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
            result=scan(root, ['termux'])
            self.assertEqual(result,scan(root,['termux']))
            paths={r['path'] for r in result['findings']}
            self.assertEqual(paths,{'lib/render.py','profiles/termux/colors.toml'})
            self.assertEqual({r['kind'] for r in result['findings']},{'color','icon','formatting'})
            self.assertNotIn('#123456',json.dumps(result))
            self.assertNotIn('must not execute',json.dumps(result))
            self.assertEqual(result['skipped']['symlink'],1)
            self.assertEqual(before,{str(p):p.stat().st_mtime_ns for p in root.rglob('*') if p.is_file() and not p.is_symlink()})


if __name__=='__main__':unittest.main()
