"""Prepare private, replaceable native startup bundles; never install dotfiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
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
from environment import declarations, TOKEN, TOOL_PATHS
import mise_shims


def shell_value(template):
    parts, cursor = [], 0
    for match in TOKEN.finditer(template):
        parts.extend((shlex.quote(template[cursor:match.start()]), '"${' + match[1] + '-}"'))
        cursor = match.end()
    parts.append(shlex.quote(template[cursor:]))
    return ''.join(parts)


class Compiler:
    def __init__(self, root, shell, *, early=False):
        self.root, self.shell, self.early = root, shell, early
        self.inputs = set()
        self.missing_inputs = set()
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
                    path = str(self.root / group['name'])
                    line = block.a + offset + 1
                    previous = result[-1] if result else None
                    if (previous and previous['file'] == path and previous['generated_end'] + 1 == number
                            and previous['line'] + number - previous['generated_start'] == line):
                        previous['generated_end'] = number
                    else:
                        result.append(dict(generated_start=number, generated_end=number, file=path, line=line))
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
            # The module can return immediately outside tmux. Keep that return
            # scoped to its file so full startup still runs later profile hooks.
            if name == 'shells/shared/tmux-workspaces.sh':
                return self.module(name, match[0], 'source')
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
        shim_inputs = []
        context, self.mise_guard = mise_shims.startup_context(self.root, profile, generated.scalars)
        shim = mise_shims.resolve(context, False, shim_inputs)
        self.inputs.add(LIB / 'mise_shims.py')
        for path in shim_inputs:
            (self.inputs if path.exists() else self.missing_inputs).add(path)
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
        from profile_config import settings as profile_settings, legacy_directory
        directory = profile['layers'][-1]['root'] if profile['layers'] else legacy_directory()
        setting_rows = ['__path\t' + str(directory) + '\tprofile']
        setting_rows += [key + '\t' + row['value'] + '\t' + row['source'] for key, row in profile_settings(self.root, profile).items() if key != 'files.backup']
        from style_config import Styles
        styles = Styles(self.root, profile)
        setting_rows += ['\t'.join(row) for row in styles.rows()]
        from profile_config import formatting_rows, help_rows
        from config_values import Controls
        controls = Controls(self.root, profile)
        self.inputs.update(styles.startup_inputs(controls))
        setting_rows += ['\t'.join(row) for row in formatting_rows(self.root,profile,controls=controls)]
        setting_rows += ['\t'.join(row) for row in help_rows(self.root,profile,styles=styles,controls=controls)]
        from completion_preferences import rows as completion_rows
        for row in completion_rows(styles=styles,controls=controls):
            setting_rows.append('\t'.join(row))
            if row[0] in ('__completion.watch', '__completion.watch.hex'):
                # Guard missing inputs with shell existence checks. Watching a
                # distant home/state ancestor would invalidate on unrelated I/O.
                path = Path(bytes.fromhex(row[1]).decode() if row[0].endswith('.hex') else row[1])
                if path.exists(): self.inputs.add(path)
                else: self.missing_inputs.add(path)
        from cli_preferences import rows as cli_rows
        setting_rows += ['\t'.join(row) for row in cli_rows(controls)]
        self.inputs.add(LIB/'cli_preferences.py')
        self.inputs.update((LIB/'config_values.py',LIB/'row_layout.py',LIB/'help_presentation.py'))
        defaults=self.root/'default/config.json'
        if defaults.is_file(): self.inputs.add(defaults)
        if defaults.parent.is_dir(): self.inputs.add(defaults.parent)
        body = 'typeset -g _DOTS_PROFILE_SETTINGS_CHECKOUT=' + shlex.quote(str(self.root)) + '\n'
        body += 'typeset -ga _DOTS_PROFILE_SETTING_ROWS=(' + ' '.join(map(shlex.quote, setting_rows)) + ')\n'
        body += self.module('lib/dots/shell/config.bash', self.read('lib/dots/shell/config.bash') + '\n_dots_config_load || return\n')
        body += self.module('lib/dots/shell/environment.bash', self.read('lib/dots/shell/environment.bash')) + '\n'
        body += '_dots_mise_shims=' + shlex.quote(str(shim) if shim else '') + '\n'
        body += 'if [[ ${_DOTS_STARTUP_MODE:-integration} == early ]]; then _dots_shell_paths early; return 0; fi\n'
        if self.early:
            return body, profile
        profile_paths = [str(Path(row['root']) / p) for row in reversed(profile['layers'])
                         for p in row.get('path', ['bin', 'scripts'])]
        if shim:
            profile_paths.append(str(shim))
        body += '_dots_profile_path=(' + ' '.join(map(shlex.quote, profile_paths)) + ')\n'
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
        # Add installed tools before profile/checkout directories establish
        # their precedence. Expansions remain local to this shell and HOME.
        for placement, variable, suffix in TOOL_PATHS:
            ending = '/' + suffix if suffix else ''
            body += f'[[ -z "${{{variable}:-}}" ]] || _dots_tool_path {placement} "${{{variable}}}{ending}"\n'
        body += '_dots_env_publish_origins\n'
        body += 'export DOTS_PROFILE_CHECKOUT=' + shlex.quote(str(self.root)) + '\n'
        body += 'export DOTS_PROFILE_BIN_PATHS=' + shlex.quote(os.pathsep.join(str(Path(row['root'])/'bin') for row in reversed(profile['layers']))) + '\n'
        body += self.module('lib/dots/shell/profile-paths.bash', self.read('lib/dots/shell/profile-paths.bash')) + '\n'
        body += '[[ $- == *i* ]] || return 0\n'
        body += '_dots_startup_path=$PATH _dots_startup_roots="$DOTBIN:$DOTSCRIPTS:$THEMESBIN:${dots_options[DOTS_INIT_COMMANDS]}"\n'
        # Full startup order remains shell-owned; lightweight init skips it.
        body += 'if [[ ${_DOTS_STARTUP_MODE:-integration} == full ]]; then\n:\n'
        if self.shell == 'zsh': body += "typeset -gA zsh\nunset 'zsh[profile_local]'\n"
        for stage in ('init', 'local'):
            if stage == 'local':
                body += self.expand(f'shells/{self.shell}/interactive.{self.shell}')
            for row in profile['layers']:
                hook = Path(row['root'])/'shells'/f'{stage}.{self.shell}'
                # Check at use time. Personal code and its values are never compiled.
                origin = 'profile-' + row['id'].replace('/', '-')
                private = ' 1' if stage == 'local' else ''
                file = shlex.quote(str(hook))
                # A wrapper function would scope Bash's declare and Zsh's
                # typeset to the wrapper instead of the user's shell.
                body += (f'if [[ -r {file} ]]; then\n_dots_hook_snapshot\n'
                         f'_dots_debug_event begin {file} source\nsource {file}\n'
                         f'_dots_debug_event end {file} source "$?"\n'
                         f'_dots_hook_record {shlex.quote(origin)}{private}\nfi\n')
        body += '\nelse\n' + self.module('lib/dots/shell/integration.bash', self.read('lib/dots/shell/integration.bash').split('[[ $- == *i* ]] || return 0\n', 1)[1])
        body += '\nfi\n_dots_retire_environment\ntrue\n'
        return body, profile


GENERATION = re.compile('[0-9a-f]{24}')
BUNDLE_HEADER = '# dots startup bundle 2'
PAYLOADS = {'bundle', 'guard', 'manifest.json'}


def pointer(path):
    """Read only our small, regular ASCII publication pointers."""
    if not path.exists() and not path.is_symlink():
        return None
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != 25:
        raise ValueError('invalid startup pointer: ' + str(path))
    value = path.read_text('ascii').rstrip('\n')
    if not GENERATION.fullmatch(value):
        raise ValueError('invalid startup pointer: ' + str(path))
    return value


def publish_pointer(path, value):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(value + '\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def generation_version(directory):
    """Recognize only complete private generations owned by this user."""
    if not GENERATION.fullmatch(directory.name):
        return None
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        return None
    if {p.name for p in directory.iterdir()} != PAYLOADS:
        return None
    for filename in PAYLOADS:
        child = (directory / filename).lstat()
        if (not stat.S_ISREG(child.st_mode) or child.st_uid != info.st_uid or child.st_nlink != 1
                or child.st_dev != info.st_dev or child.st_mode & 0o022):
            return None
    manifest = directory / 'manifest.json'
    if manifest.stat().st_size > 8 * 1024 * 1024:
        return None
    try:
        metadata = json.loads(manifest.read_bytes())
    except (ValueError, UnicodeError):
        return None
    if (isinstance(metadata, dict) and type(metadata.get('version')) is int and metadata['version'] in (1, 2) and metadata.get('shell') in ('bash', 'zsh')
            and isinstance(metadata.get('root'), str) and Path(metadata['root']).is_absolute()
            and isinstance(metadata.get('inputs'), list) and isinstance(metadata.get('source_map'), list)):
        # Both formats use the first 24 hex digits of SHA-256(bundle + guard).
        # Matching payloads distinguish this producer from a foreign directory.
        hasher = hashlib.sha256()
        for filename in ('bundle', 'guard'):
            file = directory / filename
            if file.stat().st_size > 8 * 1024 * 1024:
                return None
            with file.open('rb') as stream:
                for block in iter(lambda: stream.read(65536), b''):
                    hasher.update(block)
        if hasher.hexdigest()[:24] == directory.name:
            return metadata['version']
    return None


def prepare(root, shell, destination, early=False, observed=None):
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
        if observed is not None:
            try:
                current = pointer(destination/'current')
            except (FileNotFoundError, ValueError):
                current = None
            if current and current != observed:
                # A concurrent shell published while this reader was waiting.
                # Its native guard decides whether that generation serves this
                # mode. In particular a script must never downgrade a fresh rc.
                return destination/current
        compiler = Compiler(root, shell, early=early)
        body, profile = compiler.build()
        body = (BUNDLE_HEADER + '\n'
                'source "$_dots_startup_cache/$_dots_startup_generation/guard" || return 1\n'
                '_dots_startup_entered=1\n' + body)
        inputs = sorted(compiler.inputs)
        for path, expected in compiler.observed.items():
            st = path.stat()
            if expected != (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns): raise ValueError('startup input changed during preparation')
        signature = subprocess.check_output(['stat','-c','%d:%i:%s:%y:%z','--', *map(str,inputs)], text=True).rstrip('\n')
        guard = '[[ $DOTS == ' + shlex.quote(str(root)) + ' && ${ZSH_VERSION:-${BASH_VERSION:-}} == ' + shlex.quote(os.environ.get('DOTS_BUILD_SHELL_VERSION','')) + ' ]] || return 1\n'
        if early:
            guard += '[[ ${_DOTS_STARTUP_MODE:-integration} == early ]] || return 1\n'
        for key, values in compiler.mise_guard.items():
            comparisons = ['${' + key + ':-} == ' + shlex.quote(value) for value in values]
            guard += '[[ ' + ' || '.join(comparisons) + ' ]] || return 1\n'
        for path in sorted(compiler.missing_inputs):
            guard += '[[ ! -e ' + shlex.quote(str(path)) + ' ]] || return 1\n'
        guard += '_dots_bundle_inputs=(' + ' '.join(map(lambda p: shlex.quote(str(p)),inputs)) + ')\n'
        guard += '[[ $(command stat -c \'%d:%i:%s:%y:%z\' -- "${_dots_bundle_inputs[@]}" 2>/dev/null) == ' + shlex.quote(signature) + ' ]]\n'
        shell_bin = shutil.which(shell)
        if not shell_bin: raise ValueError('native shell unavailable for bundle validation')
        syntax_flags = ['-dfn'] if shell == 'zsh' else ['--noprofile', '--norc', '-n']
        if subprocess.run([shell_bin, *syntax_flags], input=body, text=True, capture_output=True, timeout=10).returncode:
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
                (temporary/'manifest.json').write_text(json.dumps(dict(version=2,root=str(root),shell=shell,profile=profile['current'],inputs=list(map(str,inputs)), modules=compiler.modules, source_map=compiler.source_map(body), signature=signature, shell_version=os.environ.get('DOTS_BUILD_SHELL_VERSION',''), metadata=[dict(path=str(p),size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,ctime_ns=p.stat().st_ctime_ns) for p in inputs]),separators=(',',':'))+'\n')
                for p in temporary.iterdir(): p.chmod(0o600)
                temporary.rename(generation)
            finally:
                if temporary.exists(): shutil.rmtree(temporary)
        elif generation_version(generation) != 2:
            raise ValueError('unrecognized startup generation at publication destination')
        current = destination / 'current'
        try:
            old = pointer(current)
        except ValueError:
            # A torn regular pointer is replaceable. Preserve foreign objects.
            if not stat.S_ISREG(current.lstat().st_mode):
                raise
            old = None
        if old != digest:
            if old:
                publish_pointer(destination / 'previous', old)
            publish_pointer(destination / 'current', digest)
        retained = {digest, pointer(destination / 'previous')}
        # This runs only under the publisher lock. Old-format and foreign data
        # are never reclaimed automatically, including pre-upgrade diagnostics.
        for entry in destination.iterdir():
            if entry.name in retained or not GENERATION.fullmatch(entry.name) or entry.is_symlink():
                continue
            # Skip historical payloads cheaply even if a previous install
            # accumulated hundreds of manifests. Cleanup offers those for review.
            bundle = entry / 'bundle'
            if not bundle.is_file() or bundle.is_symlink():
                continue
            with bundle.open('rb') as stream:
                is_new = stream.readline(64) == (BUNDLE_HEADER + '\n').encode()
            if is_new and generation_version(entry) == 2:
                for filename in PAYLOADS:
                    (entry / filename).unlink()
                entry.rmdir()
        return generation


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shell',choices=('bash','zsh'),required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--early', action='store_true', help='prepare only the noninteractive Zsh environment')
    parser.add_argument('--observed', help='generation already tried by the native reader')
    args=parser.parse_args()
    try: prepare(Path(os.environ.get('DOTS') or LIB.parents[1]).resolve(),args.shell,args.cache,
                 early=args.early,observed=args.observed)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('dots startup: '+str(error),file=sys.stderr);sys.exit(1)
