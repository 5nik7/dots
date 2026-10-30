"""Prepare private, replaceable native startup bundles; never install dotfiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import errno

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB / 'files'))
from file_platform import lock, open_nofollow
from profiles import resolve, SENSITIVE
from environment import declarations, TOKEN


def shell_value(template):
    parts, cursor = [], 0
    for match in TOKEN.finditer(template):
        parts.extend((shlex.quote(template[cursor:match.start()]), '"${' + match[1] + '-}"'))
        cursor = match.end()
    parts.append(shlex.quote(template[cursor:]))
    return ''.join(parts)


class Compiler:
    def __init__(self, root, shell):
        self.root, self.shell = root, shell
        self.inputs = set()
        self.stack = set()
        self.observed = {}
        self.modules = []
        self.source_text = {}

    def read(self, relative):
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root): raise ValueError('startup source escapes checkout')
        self.inputs.add(path)
        before = path.stat()
        text = path.read_text()
        after = path.stat()
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(after): raise ValueError('startup input changed during preparation')
        self.observed[path] = identity(after)
        self.source_text[relative] = text
        return text

    def source_map(self, body):
        """Map unchanged authored lines within their own compiled module scope."""
        import difflib
        stack, groups = [], []
        for number, line in enumerate(body.splitlines(), 1):
            if line.startswith('_dots_debug_event begin '):
                parts = shlex.split(line)
                group = dict(name=parts[2], kind=parts[3], lines=[])
                groups.append(group); stack.append(group)
            elif line.startswith('_dots_debug_event end '):
                if stack: stack.pop()
            elif stack: stack[-1]['lines'].append((number, line))
        result = []
        for group in groups:
            if group['kind'] != 'inlined' or group['name'] not in self.source_text: continue
            source = self.source_text[group['name']].splitlines()
            generated = group['lines']
            for block in difflib.SequenceMatcher(None, source, [line for _,line in generated], autojunk=False).get_matching_blocks():
                for offset in range(block.size):
                    number = generated[block.b+offset][0]
                    result.append(dict(generated_start=number, generated_end=number,
                                       file=str(self.root/group['name']), line=block.a+offset+1))
        return result

    def module(self, relative, body, kind="inlined"):
        self.modules.append(relative)
        label = shlex.quote(relative)
        return '\n_dots_debug_event begin ' + label + ' ' + kind + '\n' + body + '\n_dots_debug_event end ' + label + ' ' + kind + ' "$?"\n'

    def expand(self, relative):
        if relative in self.stack: raise ValueError('recursive startup source: ' + relative)
        self.stack.add(relative)
        body = self.read(relative)
        # Inline only plain, unconditional authored module imports. Runtime
        # plugins, theme readers, completion autoloads and private hooks keep
        # their own source lifecycle and are never copied into a bundle.
        def replace(match):
            expression = match[1]
            name = expression.replace('$ZSH/', 'shells/zsh/').replace('$DOTS/', '')
            if name == 'lib/dots/shell/init.zsh': name = 'lib/dots/shell/init.bash'
            if name == 'lib/dots/shell/init.bash':
                return self.module('lib/dots/shell/integration.bash', self.read('lib/dots/shell/integration.bash').split('[[ $- == *i* ]] || return 0\n', 1)[1])
            if name in ('shells/shared/platform.sh', 'shells/shared/app-env.sh'): return ''
            if name.startswith(('shells/shared/', 'shells/bash/core/', 'shells/zsh/core/')) or name in ('shells/zsh/functions.zsh','shells/zsh/options.zsh','shells/zsh/fzf.zsh','shells/zsh/completions.zsh'):
                return '\n# ' + name + '\n' + self.expand(name)
            return self.module(name, match[0], "source")
        body = re.sub(r'^source "(\$(?:DOTS|ZSH)/[^"\n]+)"\s*$', replace, body, flags=re.M)
        if relative == 'shells/zsh/interactive.zsh':
            for call, label in (('_dots_completion_plugins','completion plugins'),('_dots_shell_prompt','theme and prompt hooks'),('_dots_widget_plugins','widget plugins')):
                body = re.sub('^'+call+'$', lambda match, label=label: self.module(label, match[0], 'phase'), body, flags=re.M)
        self.stack.remove(relative)
        return self.module(relative, body)

    def build(self):
        profile = resolve(self.root)
        from profile_environment import Model
        generated = Model(self.root, profile)
        self.inputs.update(generated.inputs)
        release = Path(os.environ.get('TERMUX__PREFIX') or os.environ.get('PREFIX', '/usr')) / 'etc/os-release' if profile['facts']['platform'] == 'termux' else Path('/etc/os-release')
        if release.is_file(): self.inputs.add(release)
        for name in ('startup.py', 'profile_config.py', 'profiles.py', 'platform_info.py', 'environment.py', 'shell/environment.json', 'shell/settings.tsv', 'shell/paths.tsv'):
            self.inputs.add(LIB / name)
        for layer in profile['layers']: self.inputs.add(Path(layer['root']) / 'profile.json')
        # Directory metadata makes adding a distro/manifest invalidate old bundles.
        for p in [self.root / 'profiles', *[self.root / 'profiles' / name for name in ('termux','linux','wsl','windows')]]:
            if p.is_dir(): self.inputs.add(p)
            if (p / 'distros').is_dir():
                self.inputs.add(p / 'distros')
                self.inputs.update(child for child in (p / 'distros').iterdir() if child.is_dir())
        from profile_config import settings as profile_settings, directory as config_directory
        setting_rows = ['__path\t' + str(config_directory(self.root)) + '\tprofile']
        setting_rows += [key + '\t' + row['value'] + '\t' + row['source'] for key, row in profile_settings(self.root, profile).items() if key != 'files.backup']
        from style_config import Styles
        styles = Styles(self.root, profile)
        self.inputs.update(styles.startup_inputs())
        setting_rows += ['\t'.join(row) for row in styles.rows()]
        body = 'typeset -g _DOTS_PROFILE_SETTINGS_CHECKOUT=' + shlex.quote(str(self.root)) + '\n'
        body += 'typeset -ga _DOTS_PROFILE_SETTING_ROWS=(' + ' '.join(map(shlex.quote, setting_rows)) + ')\n'
        body += self.module('lib/dots/shell/config.bash', self.read('lib/dots/shell/config.bash') + '\n_dots_config_load || return\n')
        body += self.module('lib/dots/shell/environment.bash', self.read('lib/dots/shell/environment.bash')) + '\n'
        body += self.module('lib/dots/shell/environment_runtime.bash', self.read('lib/dots/shell/environment_runtime.bash')) + '\n'
        body += 'export DOTS_PROFILE=' + shlex.quote(profile['current']) + '\n'
        body += 'export DOTS_PROFILE_LAYERS=' + shlex.quote(' '.join(row['id'] for row in profile['layers'])) + '\n'
        body += 'export DOTS_ARCH=' + shlex.quote(profile['facts']['architecture']) + '\n'
        body += generated.shell(self.shell)
        for key, (value, origin) in declarations(self.root, profile).items():
            if SENSITIVE.search(key) and value and not TOKEN.fullmatch(value): raise ValueError('sensitive defaults must reference an environment variable')
            if value == '@editor':
                body += '_dots_editor=vi\nfor _dots_candidate in nvim vim vi code nano; do\n  if command -v "$_dots_candidate" >/dev/null 2>&1; then _dots_editor=$_dots_candidate; break; fi\ndone\n'
                value = '${_DOTS_EDITOR}'
                expression = '"$_dots_editor"'
            else: expression = shell_value(value)
            body += '_dots_env_default ' + shlex.quote(key) + ' ' + expression + ' ' + shlex.quote(origin) + '\n'
        body += '_dots_env_publish_origins\n'
        profile_paths = []
        for row in reversed(profile['layers']):
            profile_paths.extend(str(Path(row['root']) / p) for p in row.get('path', ['bin','scripts']))
        body += 'export DOTS_PROFILE_CHECKOUT=' + shlex.quote(str(self.root)) + '\n'
        body += 'export DOTS_PROFILE_BIN_PATHS=' + shlex.quote(os.pathsep.join(str(Path(row['root'])/'bin') for row in reversed(profile['layers']))) + '\n'
        body += '_dots_profile_path=(' + ' '.join(map(shlex.quote, profile_paths)) + ')\n'
        body += self.module('lib/dots/shell/profile-paths.bash', self.read('lib/dots/shell/profile-paths.bash')) + '\n'
        body += '[[ $- == *i* ]] || return 0\n'
        # Full startup order remains shell-owned; lightweight init skips it.
        body += 'if [[ ${_DOTS_STARTUP_MODE:-integration} == full ]]; then\n:\n'
        if self.shell == 'zsh': body += 'typeset -gA zsh\n'
        for row in profile['layers']:
            hook = Path(row['root']) / 'shells' / ('init.' + self.shell)
            # Existence is checked at runtime: private/custom code is never cached.
            body += '_dots_hook_source ' + shlex.quote(str(hook)) + ' ' + shlex.quote('profile-' + row['id'].replace('/', '-')) + '\n'
        body += self.expand('shells/' + self.shell + '/interactive.' + ('zsh' if self.shell == 'zsh' else 'bash'))
        body += '\nelse\n' + self.module('lib/dots/shell/integration.bash', self.read('lib/dots/shell/integration.bash').split('[[ $- == *i* ]] || return 0\n', 1)[1])
        body += '\nfi\n_dots_retire_environment\ntrue\n'
        return body, profile


def prepare(root, shell, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.is_symlink(): raise ValueError('startup cache must not be a symlink')
    lockpath = destination / 'build.lock'
    with os.fdopen(open_nofollow(lockpath, os.O_CREAT | os.O_RDWR, 0o600), 'a+b') as handle:
        deadline = time.monotonic() + 5
        while True:
            try:
                lock(handle)
                break
            except OSError as error:
                if error.errno not in (errno.EAGAIN, errno.EACCES) or time.monotonic() >= deadline: raise
                time.sleep(0.025)
        compiler = Compiler(root, shell)
        body, profile = compiler.build()
        inputs = sorted(compiler.inputs)
        for path, expected in compiler.observed.items():
            st = path.stat()
            if expected != (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns): raise ValueError('startup input changed during preparation')
        signature = subprocess.check_output(['stat','-c','%d:%i:%s:%y:%z','--', *map(str,inputs)], text=True).rstrip('\n')
        guard = '[[ $DOTS == ' + shlex.quote(str(root)) + ' && ${ZSH_VERSION:-${BASH_VERSION:-}} == ' + shlex.quote(os.environ.get('DOTS_BUILD_SHELL_VERSION','')) + ' ]] || return 1\n'
        guard += '_dots_bundle_inputs=(' + ' '.join(map(lambda p: shlex.quote(str(p)),inputs)) + ')\n'
        guard += '[[ $(command stat -c \'%d:%i:%s:%y:%z\' -- "${_dots_bundle_inputs[@]}" 2>/dev/null) == ' + shlex.quote(signature) + ' ]]\n'
        shell_bin = shutil.which(shell)
        if not shell_bin: raise ValueError('native shell unavailable for bundle validation')
        if subprocess.run([shell_bin, '-n'], input=body, text=True, capture_output=True, timeout=10).returncode:
            raise ValueError('generated startup bundle failed native syntax validation')
        # Immutable generation + atomic pointer: readers never pair a new guard
        # with an old body. No environment values are stored here.
        digest = hashlib.sha256((body+guard).encode()).hexdigest()[:24]
        generation = destination / digest
        if not generation.exists():
            temporary = Path(tempfile.mkdtemp(prefix='.build-', dir=destination))
            try:
                (temporary/'bundle').write_text(body)
                (temporary/'guard').write_text(guard)
                (temporary/'manifest.json').write_text(json.dumps(dict(version=1,root=str(root),shell=shell,profile=profile['current'],inputs=list(map(str,inputs)), modules=compiler.modules, source_map=compiler.source_map(body), signature=signature, shell_version=os.environ.get('DOTS_BUILD_SHELL_VERSION',''), metadata=[dict(path=str(p),size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,ctime_ns=p.stat().st_ctime_ns) for p in inputs]),indent=2)+'\n')
                for p in temporary.iterdir(): p.chmod(0o600)
                temporary.rename(generation)
            finally:
                if temporary.exists(): shutil.rmtree(temporary)
        fd, temporary = tempfile.mkstemp(prefix='.current-', dir=destination)
        with os.fdopen(fd,'w') as out: out.write(digest+'\n');out.flush();os.fsync(out.fileno())
        os.replace(temporary,destination/'current')
        return generation


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shell',choices=('bash','zsh'),required=True)
    parser.add_argument('--cache',type=Path,required=True)
    args=parser.parse_args()
    try: prepare(Path(os.environ.get('DOTS') or LIB.parents[1]).resolve(),args.shell,args.cache)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('dots startup: '+str(error),file=sys.stderr);sys.exit(1)
