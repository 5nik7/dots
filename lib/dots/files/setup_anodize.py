"""Owned, source-bound Anodize build preparation; publication stays journaled."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from transactions import digest, private_directory


class Build:
    def __init__(self, installation):
        self.installation = installation
        self.source = installation.root/'plugins/anodize/engine'
        self.inputs = sorted(p for p in self.source.rglob('*')
                             if '.build' not in p.parts and '.git' not in p.parts
                             and p.is_file() and (p.suffix == '.go' or p.name in ('go.mod', 'go.sum')))
        signature = hashlib.sha256()
        for path in self.inputs:
            if path.is_symlink(): raise ValueError('Anodize source must be regular: '+str(path))
            installation.guard(path)
            signature.update(str(path.relative_to(self.source)).encode()+b'\0'+digest(path).encode())
        self.identity = signature.hexdigest()
        self.minimum = re.search(r'(?m)^go ([0-9.]+)$', (self.source/'go.mod').read_text())[1]
        self.destination = self.source/'.build'/('anodize-engine.exe' if installation.platform == 'windows' else 'anodize-engine')
        self.artifact = None

    def prepare(self):
        go = shutil.which('go')
        if not go: raise ValueError('Anodize requires Go '+self.minimum+' or newer')
        root = self.installation.state/'setup-builds/anodize'/self.identity
        private_directory(root)
        env = dict(os.environ, GOTOOLCHAIN='local', GOENV='off', GOWORK='off', GOFLAGS='',
                   GOPATH=str(root/'go'), GOCACHE=str(root/'cache'), GOMODCACHE=str(root/'modules'))
        for key in ('GOOS', 'GOARCH', 'GOROOT', 'GOPROXY', 'GOSUMDB'):
            env.pop(key, None)
        if getattr(self, 'offline', False): env.update(GOPROXY='off', GOSUMDB='off')
        version = subprocess.run([go, 'version'], env=env, capture_output=True, text=True, timeout=20, check=True).stdout
        match = re.search(r'go(\d+)\.(\d+)(?:\.(\d+))?', version)
        minimum = tuple(int(v) for v in (self.minimum.split('.')+['0','0'])[:3])
        if not match or tuple(int(v or 0) for v in match.groups()) < minimum:
            raise ValueError('installed Go is older than Anodize go.mod requirement '+self.minimum)
        binary, record = root/self.destination.name, root/'verified.json'
        if binary.is_file() and not binary.is_symlink() and record.is_file() and not record.is_symlink():
            if json.loads(record.read_text()) == dict(schema=1, source=self.identity, binary=digest(binary), toolchain=version.strip()):
                self.artifact = binary
                return dict(reused=True, source=self.identity)
        with tempfile.TemporaryDirectory(prefix='work-', dir=root) as work:
            work = Path(work)
            for source in self.inputs:
                target = work/source.relative_to(self.source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            for args in (['test', './...'], ['build', '-trimpath', '-o', str(work/self.destination.name), './cmd/anodize-engine']):
                subprocess.run([go, *args], cwd=work, env=env, stdout=__import__('sys').stderr,
                               stderr=__import__('sys').stderr, check=True, timeout=600)
            from setup_stages import verify
            verify(self.installation.guards)
            staged = work/self.destination.name
            from transactions import Store
            Store(self.installation.state).apply('prepare-anodize', [dict(path=str(binary), source=str(staged)),
                dict(path=str(record), data=dict(schema=1, source=self.identity, binary=digest(staged), toolchain=version.strip()))],
                {str(binary):digest(binary), str(record):digest(record), str(staged):digest(staged)})
        self.artifact = binary
        return dict(reused=False, source=self.identity)

    def publish(self, installation):
        if self.artifact is None: raise ValueError('Anodize artifact was not verified')
        installation.add('dots:anodize:engine', self.destination, source=self.artifact)
