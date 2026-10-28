import base64
import json
import os
from release_support import ReleaseHarness,core
transport=core.ui_module('argv_transport')
class ArgvTransport(ReleaseHarness):
    def envelope(self,arguments,**extra):
        data={'version':1,'host':os.name,'argv':arguments,**extra}
        return [transport.FLAG,base64.b64encode(json.dumps(data).encode()).decode()]
    def test_literal_round_trip_and_alias_scope(self):
        values=['theme','import','space ü path "quote"\\','','--','all','y','-theme']
        self.assertEqual(transport.decode(self.envelope(values))[0],values)
        self.assertEqual(transport.decode(self.envelope(['-list','--json']))[0],['--list','--json'])
        self.assertEqual(transport.decode(self.envelope(['theme','save','-list']))[0],['theme','save','-list'])
        self.assertEqual(transport.decode(self.envelope(['-list','--json']),aliases=False)[0],['-list','--json'])
    def test_real_entry_and_json_errors(self):
        self.assertIn(core.VERSION,self.invoke(*self.envelope(['--version'])).stdout)
        result=self.invoke(*self.envelope(['--json','module','list']))
        self.assertEqual(json.loads(result.stdout),{'modules':[]})
        result=self.invoke(*self.envelope(['--json','theme','apply']),code=2)
        self.assertEqual(json.loads(result.stderr)['code'],2)
    def test_malformed_and_wrong_platform(self):
        for args in ([transport.FLAG,'notbase64'],self.envelope(['\x00']),self.envelope(['x'],version=2),self.envelope(['x'],host='nt' if os.name=='posix' else 'posix')):
            with self.assertRaises(ValueError):transport.decode(args)
            self.invoke(*args,code=3)
