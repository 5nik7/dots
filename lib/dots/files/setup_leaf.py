"""Pinned, isolated Leaf acquisition and verified artifact reuse."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from transactions import digest, parents_safe, private_directory, Store

COMMIT = '140e55858c98df50ba52fc4ab7bad277a31ab73f'
SOURCE = 'https://github.com/RivoLink/leaf.git'
VERSION = 'leaf 1.28.2+dots.1'


def sha(path):
    with Path(path).open('rb') as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024*1024), b''): value.update(block)
        return value.hexdigest()


def execute(argv, *, cwd=None, env=None, capture=False):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE if capture else sys.stderr, stderr=subprocess.PIPE if capture else sys.stderr)
    if result.returncode:
        raise ValueError('Leaf preparation failed: '+str(argv[0])+' '+str(argv[1])+(
            ': '+result.stderr[-1000:] if capture else '; see preceding build output'))
    return result.stdout.strip() if capture else ''


class Build:
    def __init__(self, installation):
        self.installation = installation
        self.patch = installation.root/'tools/patches/leaf-1.28.2-dots-syntax.patch'
        installation.guard(self.patch)
        self.consumer = installation.root/'tools/test_leaf_theme.py'
        installation.guard(self.consumer)
        home = Path(os.environ.get('HOME') or Path.home())
        cache = Path(os.environ.get('XDG_CACHE_HOME') or
            (os.environ.get('LOCALAPPDATA', home/'AppData/Local') if installation.platform == 'windows' else home/'.cache'))
        self.base = cache/'dots/builds/leaf'
        self.target = home/'.local/bin'/('leaf.exe' if installation.platform == 'windows' else 'leaf')
        # Reject foreign links and drift before fetching/building anything.
        installation.guard(self.target)
        owned = installation.entries.get(str(self.target))
        if self.target.is_symlink() and not owned:
            raise ValueError('Leaf command is an unrelated link; review it before installation: '+str(self.target))
        if owned and installation.guards[str(self.target)] != owned['after']:
            raise ValueError('installer-owned Leaf command changed; preserve and review it')
        self.result = None

    def prepare(self):
        sysroot = Path(execute(['rustc', '--print', 'sysroot'], capture=True))
        suffix = '.exe' if self.installation.platform == 'windows' else ''
        cargo = sysroot/'bin'/('cargo'+suffix)
        rustc = sysroot/'bin'/('rustc'+suffix)
        if not cargo.is_file() or not rustc.is_file(): raise ValueError('Rust toolchain binaries are unavailable')
        identity = dict(schema=1, source=SOURCE, commit=COMMIT, patch=sha(self.patch),
                        platform=self.installation.platform, architecture=platform.machine(),
                        rustc=execute([rustc, '-vV'], capture=True), cargo=execute([cargo, '-V'], capture=True),
                        consumer=sha(self.consumer))
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        directory = self.base/key
        parents_safe(directory/'verified.json')
        if directory.is_symlink(): raise ValueError('Leaf build directory cannot be a link')
        manifest = directory/'verified.json'
        binary = directory/'target/release'/('leaf'+suffix)
        if manifest.is_file() and not manifest.is_symlink():
            doc = json.loads(manifest.read_text())
            if doc.get('identity') == identity and binary.is_file() and not binary.is_symlink() and sha(binary) == doc.get('sha256'):
                if execute([binary, '--version'], capture=True) != VERSION: raise ValueError('cached Leaf reports an unexpected version')
                self.result = dict(path=str(binary), reused=True, identity=identity, sha256=doc['sha256'])
                return self.result
            raise ValueError('Leaf build cache changed; preserve and review '+str(directory))
        private_directory(directory)
        # Claim only an empty/new directory. Incomplete owned builds can resume;
        # arbitrary pre-existing source trees are never reset or patched twice.
        marker = directory/'identity.json'
        if marker.exists():
            if marker.is_symlink() or json.loads(marker.read_text()) != identity:
                raise ValueError('Leaf build ownership differs; review '+str(directory))
        elif any(directory.iterdir()):
            raise ValueError('Leaf build directory lacks ownership evidence: '+str(directory))
        else:
            Store(self.installation.state).apply('setup-leaf-build', [dict(path=str(marker),data=identity)],
                {str(marker):None}, retain=True)
        build_home = directory/'home'
        private_directory(build_home)
        env = {key:value for key,value in os.environ.items() if not key.startswith('GIT_')}
        env.update(HOME=str(build_home), USERPROFILE=str(build_home), XDG_CONFIG_HOME=str(build_home/'config'),
            XDG_STATE_HOME=str(build_home/'state'), XDG_CACHE_HOME=str(build_home/'cache'),
            XDG_DATA_HOME=str(build_home/'data'), APPDATA=str(build_home/'Roaming'), LOCALAPPDATA=str(build_home/'Local'),
            CARGO_HOME=str(directory/'cargo'), CARGO_TARGET_DIR=str(directory/'target'),
            RUSTC=str(rustc), PATH=str(sysroot/'bin')+os.pathsep+os.environ.get('PATH',''),
            GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
        for key in ('CARGO_ENCODED_RUSTFLAGS', 'RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER'):
            env.pop(key, None)
        source = directory/'source'
        if source.is_symlink() or (source/'.git').is_symlink():
            raise ValueError('Leaf build source cannot be a link')
        if not source.exists() or not any(source.iterdir()):
            execute(['git','init',source],env=env)
        # A failed fetch leaves only the owned empty Git directory. Retry that
        # acquisition without resetting a populated or modified checkout.
        if {p.name for p in source.iterdir()} == {'.git'} and (source/'.git').is_dir():
            execute(['git','-C',source,'-c','core.hooksPath='+str(directory/'no-hooks'),
                     'fetch','--depth=1','--no-tags','--no-recurse-submodules',SOURCE,COMMIT], env=env)
            execute(['git','-C',source,'-c','core.hooksPath='+str(directory/'no-hooks'),
                     'checkout','--detach',COMMIT],env=env)
        if source.is_symlink() or execute(['git','-C',source,'rev-parse','HEAD'],env=env,capture=True) != COMMIT:
            raise ValueError('Leaf build source does not match its pinned commit')
        applied = directory/'patched.json'
        if not applied.exists():
            if execute(['git','-C',source,'status','--porcelain'],env=env,capture=True):
                raise ValueError('incomplete Leaf patch changed its source; preserve and review the build directory')
            execute(['git','-C',source,'apply','--check',self.patch],env=env)
            execute(['git','-C',source,'apply',self.patch],env=env)
            Store(self.installation.state).apply('setup-leaf-patch', [dict(path=str(applied),data=dict(schema=1,source_digest=digest(source)))],
                {str(applied):None},retain=True)
        if applied.is_symlink() or json.loads(applied.read_text())['source_digest'] != digest(source):
            raise ValueError('patched Leaf source changed; preserve and review its owned build')
        for command in ([cargo,'test','--locked','--bin','leaf'],
                        [cargo,'clippy','--locked','--all-targets','--all-features','--','-D','warnings'],
                        [cargo,'build','--locked','--release']):
            execute(command,cwd=source,env=env)
        if execute([binary,'--version'],env=env,capture=True) != VERSION:
            raise ValueError('built Leaf reports an unexpected version')
        env['LEAF_TEST_BIN'] = str(binary)
        execute([sys.executable,'-B',self.consumer,'LeafTheme.test_real_inline_syntax_colors_and_failures',
                 'LeafTheme.test_real_dark_light_tui'],env=env,cwd=self.installation.root)
        doc = dict(schema=1,identity=identity,sha256=sha(binary))
        Store(self.installation.state).apply('setup-leaf-verified', [dict(path=str(manifest),data=doc)],
            {str(manifest):None},retain=True)
        self.result = dict(path=str(binary), reused=False, identity=identity, sha256=doc['sha256'])
        return self.result

    def publish(self, installation):
        if not self.result or sha(self.result['path']) != self.result['sha256']:
            raise ValueError('Leaf artifact changed after verification')
        installation.add('setup:leaf', self.target, source=self.result['path'])
