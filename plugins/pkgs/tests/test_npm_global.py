"""Native npm regression against a local registry and a disposable global prefix."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pkgs_lib.backends import Backend
from pkgs_lib import streams, upgrade_output

NPM = shutil.which('npm')
NODE = shutil.which('node')


@unittest.skipUnless(NPM and NODE and os.name == 'posix', 'native npm/node fixture requires POSIX')
class GlobalNpm(unittest.TestCase):
    def test_targeted_global_install_preserves_foreign_platform_package(self):
        with tempfile.TemporaryDirectory(prefix='pkgs-native-npm-') as directory:
            root=Path(directory);prefix=root/'prefix';modules=prefix/'lib/node_modules'
            target='pkgs-fixture-target';foreign='pkgs-fixture-foreign'
            for name,data in ((target,dict(name=target,version='1.0.0')),
                              (foreign,dict(name=foreign,version='1.0.0',os=['fixture-unsupported-os']))):
                path=modules/name;path.mkdir(parents=True)
                (path/'package.json').write_text(json.dumps(data))
            foreign_before=(modules/foreign/'package.json').read_bytes()
            package=dict(name=target,version='2.0.0')
            tarball='/'+target+'/-/'+target+'-2.0.0.tgz'
            archive=io.BytesIO()
            with tarfile.open(fileobj=archive,mode='w:gz') as tar:
                payload=json.dumps(package).encode();info=tarfile.TarInfo('package/package.json');info.size=len(payload)
                tar.addfile(info,io.BytesIO(payload))
            blob=archive.getvalue()
            requests=[]
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    requests.append(self.path)
                    if self.path=='/'+target:
                        version={**package,'dist':dict(tarball=f'http://127.0.0.1:{self.server.server_port}'+tarball,
                                                       shasum=hashlib.sha1(blob).hexdigest())}
                        body=json.dumps(dict(name=target,versions={'2.0.0':version},**{'dist-tags':{'latest':'2.0.0'}})).encode()
                    elif self.path==tarball:body=blob
                    else:self.send_error(404);return
                    self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                for name in ('user.npmrc','global.npmrc'):(root/name).write_text('')
                env={k:v for k,v in os.environ.items() if not k.lower().startswith('npm_') and k not in ('NODE_AUTH_TOKEN','NODE_OPTIONS')}
                env.update(HOME=str(root),XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),
                           XDG_CACHE_HOME=str(root/'cache'),XDG_DATA_HOME=str(root/'data'),TMPDIR=str(root),NO_COLOR='1',
                           NO_PROXY='127.0.0.1',no_proxy='127.0.0.1')
                common=['--global','--prefix='+str(prefix),'--cache='+str(root/'npm-cache'),
                        '--userconfig='+str(root/'user.npmrc'),'--globalconfig='+str(root/'global.npmrc'),
                        '--registry=http://127.0.0.1:'+str(server.server_port),
                        '--ignore-scripts','--no-audit','--no-fund','--no-update-notifier','--fetch-retries=0']
                npm=[NODE,str(Path(NPM).resolve())]
                broken=subprocess.run([*npm,'update',*common,'--',target],cwd=root,env=env,capture_output=True,text=True,timeout=30)
                self.assertNotEqual(broken.returncode,0,broken.stdout+broken.stderr)
                self.assertIn('EBADPLATFORM',broken.stderr)
                command=Backend('npm',True).transaction('upgrade',[target])
                self.assertEqual(command,['npm','install','--global','--',target])
                streams.npm_progress_environment(command,env)
                fixed=subprocess.run([*npm,command[1],*common,*command[3:]],cwd=root,env=env,capture_output=True,text=True,timeout=30)
                self.assertEqual(fixed.returncode,0,fixed.stdout+fixed.stderr)
                meter=Mock();summary=upgrade_output.Output('npm',{},meter)
                formatter=streams.Formatter(io.StringIO(),{'output':'raw','_manager':'npm'},summary)
                formatter.feed(fixed.stderr.encode(),final=True)
                self.assertIn('Fetched · '+target,repr(meter.update.call_args_list),fixed.stderr)
                quiet=subprocess.run([*npm,'--loglevel=silent','--version'],cwd=root,env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(quiet.returncode,0,quiet.stderr)
                self.assertEqual(quiet.stderr,'')
                self.assertEqual(json.loads((modules/target/'package.json').read_text())['version'],'2.0.0')
                self.assertEqual((modules/foreign/'package.json').read_bytes(),foreign_before)
                self.assertTrue(all(p in ('/'+target,tarball) for p in requests),requests)
            finally:server.shutdown();server.server_close();worker.join()


if __name__=='__main__':unittest.main()
