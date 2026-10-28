"""Human output is explicit; structured protocols never become default output."""
import json
from release_support import ReleaseHarness, core

class OutputPolicy(ReleaseHarness):
    def test_backup_list_human_and_explicit_json(self):
        self.write(self.config, '[directory]\nstyle="purple"\n')
        created=self.invoke('backup','create','--json')
        ident=json.loads(created.stdout)['backup']
        human=self.invoke('backup','list')
        self.assertIn(ident,human.stdout); self.assertIn('Created:',human.stdout)
        self.assertIn('Size:',human.stdout); self.assertIn('Source:',human.stdout)
        self.assertNotIn('"backups"',human.stdout); self.assertNotIn('\x1b',human.stdout)
        for arguments in [('backup','list','--json'),('--json','backup','list')]:
            result=self.invoke(*arguments)
            self.assertEqual(set(json.loads(result.stdout)),{'backups','errors'})
            self.assertEqual(result.stderr,'')
        result=self.invoke('backup','list','--json','-v')
        self.assertEqual(json.loads(result.stdout)['backups'][0]['id'],ident)
        self.assertIn('debug',result.stderr)
    def test_empty_results_and_no_writes(self):
        before=self.tree()
        for arguments,message in [(('backup','list'),'No backups'),(('module','list'),'No saved modules')]:
            result=self.invoke(*arguments)
            self.assertIn(message,result.stdout)
        self.assertEqual(before,self.tree())
    def test_explicit_human_renderer_required(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,self.env,clear=True):
            app=core.App(core.cli_module().parse(['module','list'],core.VERSION))
            with self.assertRaisesRegex(RuntimeError,'human output'):
                app.emit({'modules':[]})

    def fixture_backup(self, ident='20261013T160722Z-68908267f7dd', *, kind='stored', size=6056):
        import hashlib
        payload=b'#'+b'x'*(size-2)+b'\n'
        directory=self.store/'backups';directory.mkdir(parents=True,exist_ok=True)
        (directory/(ident+'.toml')).write_bytes(payload)
        meta={'id':ident,'kind':kind,'source':'/fixture/source.toml','reason':'before replacement',
              'sha256':hashlib.sha256(payload).hexdigest(),'symlink_target':None}
        (directory/(ident+'.json')).write_text(json.dumps(meta))
        return ident,meta

    def test_backup_roles_reset_plain_equivalence_and_sanitization(self):
        import re
        ident,_=self.fixture_backup()
        self.env.pop('NO_COLOR',None);self.env['COLUMNS']='80'
        self.env.update(DOTS_MENU_CAPTURE='1', DOTS_ICONS='never')
        colored=self.invoke('backup','list','--color','always').stdout
        plain=self.invoke('backup','list','--color','never').stdout
        for value,style in [(ident,'94'),('Backups','1;96'),('1','96')]:
            self.assertIn('\x1b['+style+'m'+value+'\x1b[0m',colored)
        self.assertEqual(re.sub(r'\x1b\[[0-9;]*m','',colored),plain)
        for value in ('Created', 'Kind', 'Size', 'Source', 'Reason', '2026-10-13 16:07:22 UTC', '6056 B'):
            self.assertIn(value, plain)
        # Data controls must never gain access to the trusted style path.
        path=self.store/'backups'/(ident+'.json');meta=json.loads(path.read_text())
        meta['reason']='before\x1b[31mEVIL\x1b[0m\u202ereplacement';path.write_text(json.dumps(meta))
        output=self.invoke('backup','list','--color','always').stdout
        self.assertNotIn('\x1b[31m',output);self.assertNotIn('\u202e',output)

    def test_backup_color_controls_tty_and_redirect(self):
        self.fixture_backup();self.env.pop('NO_COLOR',None);self.env['TERM']='xterm-256color'
        self.assertNotIn('\x1b',self.invoke('backup','list').stdout)
        code,output,_=self.run_tty(['backup','list'])
        self.assertEqual(code,0);self.assertIn('\x1b[94m',output)
        self.env['NO_COLOR']='1'
        self.assertIn('\x1b',self.invoke('backup','list','--color','always').stdout)
        self.assertNotIn('\x1b',self.run_tty(['backup','list'])[1])
        self.env.pop('NO_COLOR');self.env['TERM']='dumb'
        self.assertNotIn('\x1b',self.run_tty(['backup','list'])[1])

    def test_backup_records_width_boundary_and_complete_ids(self):
        first,_=self.fixture_backup()
        second,_=self.fixture_backup('20261014T000001Z-'+'b'*79,kind='config',size=12)
        row='  Kind: stored | Size: 6056 B'
        self.env['COLUMNS']=str(len(row))
        wide=self.invoke('backup','list').stdout
        self.assertIn(row+'\n',wide)
        self.assertIn('\n\n'+second+'\n  Created:',wide)
        self.assertLess(wide.index(first),wide.index(second))
        self.env['COLUMNS']=str(len(row)-1)
        narrow=self.invoke('backup','list').stdout
        self.assertIn('  Kind: stored\n  Size: 6056 B\n',narrow)
        self.assertIn(second+'\n',narrow)
        self.env['COLUMNS']='8'
        self.assertIn('  Kind: stored\n  Size: 6056 B\n',self.invoke('backup','list').stdout)

    def test_backup_utc_dates_unknown_and_missing_payload(self):
        ident,_=self.fixture_backup('20240229T235959Z-abcdef')
        self.fixture_backup('20260230T160722Z-abcdef')
        self.fixture_backup('legacy-name')
        for zone in ('UTC0','EST5EDT','JST-9'):
            self.env['TZ']=zone
            output=self.invoke('backup','list').stdout
            self.assertIn('Created: 2024-02-29 23:59:59 UTC',output)
            self.assertEqual(output.count('Created: unknown'),2)
        (self.store/'backups'/(ident+'.toml')).unlink()
        output=self.invoke('backup','list').stdout
        self.assertIn('Size: unavailable',output)
        self.assertIn('Payload missing; metadata remains',output)

    def test_backup_json_schema_and_presentation_io_are_unchanged(self):
        import io,os
        from contextlib import redirect_stdout,redirect_stderr
        from unittest.mock import patch
        ident,meta=self.fixture_backup()
        self.env.pop('NO_COLOR',None);before=self.tree()
        expected={'backups':[dict(meta,missing_payload=False)],'errors':[]}
        for args in [('backup','list','--json'),('--json','backup','list','--color','always')]:
            result=self.invoke(*args)
            self.assertEqual(json.loads(result.stdout),expected);self.assertNotIn('\x1b',result.stdout)
        counts=[]
        for flags in ([],['--json']):
            with patch.dict(os.environ,self.env,clear=True),patch.object(core,'read',wraps=core.read) as read,patch.object(core,'regular',wraps=core.regular) as regular,patch.object(core.subprocess,'run',side_effect=AssertionError('presentation spawned a tool')),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                self.assertEqual(core.run(['backup','list',*flags]),0)
                counts.append((read.call_count,regular.call_count))
        self.assertEqual(counts[0],counts[1])
        self.assertEqual(before,self.tree())
        (self.store/'backups'/'broken.json').write_text('{')
        result=self.invoke('backup','list',code=1)
        self.assertIn('Invalid backup broken: see stderr',result.stdout)
        self.assertIn('broken:',result.stderr)
        result=self.invoke('backup','list','--json',code=1)
        self.assertEqual(json.loads(result.stdout)['backups'],expected['backups'])
        self.assertEqual(json.loads(result.stdout)['errors'][0]['id'],'broken')

    def test_native_bash_tty_uses_shared_colors(self):
        import os,shutil
        from pathlib import Path
        if os.name != 'posix' or not shutil.which('bash'):
            self.skipTest('native Bash PTY unavailable')
        from pty_support import terminal
        ident,_=self.fixture_backup()
        self.env.pop('NO_COLOR',None);self.env['TERM']='xterm-256color'
        code,output=terminal([shutil.which('bash'),str(Path(__file__).resolve().parents[1]/'bin/blastoff'),'backup','list'],self.env,columns=80)
        self.assertEqual(code,0,output)
        self.assertIn(('\x1b[94m'+ident+'\x1b[0m').encode(),output)
        self.assertIn(b'6056 B',output)
