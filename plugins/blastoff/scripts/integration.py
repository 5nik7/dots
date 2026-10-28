"""Plan installer-owned profile fragments without executing profiles or writing.

The lifecycle driver supplies safety/atomic-write primitives. Profiles are byte
patches, not generated replacements; only exact recorded blocks may be removed.
"""
import base64
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil


def inspect(core, target):
    import stat
    for parent in [target.parent, *target.parent.parents]:
        if core.exists(parent):
            s = parent.lstat()
            if not stat.S_ISDIR(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                raise core.Failure('Unsafe integration/install parent: '+str(parent))
    if core.exists(target):
        s = target.lstat()
        if not stat.S_ISREG(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
            raise core.Failure('Refusing non-regular or linked destination: '+str(target)+
                               '; preserve the link/target and configure discovery manually, then retry.')


def absolute(core, value):
    p = core.path(str(value))
    if '..' in p.parts or any(c in str(p) for c in '\r\n\x00'):
        raise core.Failure('Unsafe integration path: '+str(p))
    return p


def zsh_root(core, home, config):
    explicit = os.environ.get('ZDOTDIR')
    chosen = absolute(core, explicit) if explicit else home
    initial = home/'.zshenv'
    if core.exists(initial):
        if initial.is_symlink():
            if explicit:
                return chosen
            raise core.Failure('Cannot inspect linked Zsh profile safely: '+str(initial)+
                               '; set ZDOTDIR explicitly for the intended regular profile, or configure discovery manually.')
        text = core.read(initial).decode('utf-8-sig')
        assignments = [line for line in text.splitlines() if re.search(r'\bZDOTDIR\s*=', line) and not line.lstrip().startswith('#')]
        for line in assignments:
            match = re.fullmatch(r'\s*(?:export\s+)?ZDOTDIR=(.*)', line)
            if not match:
                raise core.Failure('Cannot safely resolve dynamic ZDOTDIR in '+str(initial)+'; configure discovery manually and retry')
            values = shlex.split(match[1], comments=True)
            if len(values) != 1:
                raise core.Failure('Ambiguous ZDOTDIR in '+str(initial))
            value = values[0].replace('${XDG_CONFIG_HOME:-$HOME/.config}',str(config))
            for key, replacement in [('XDG_CONFIG_HOME',str(config)), ('HOME',str(home))]:
                value = value.replace('${'+key+'}',replacement).replace('$'+key,replacement)
            if '$' in value or '`' in value:
                raise core.Failure('Dynamic ZDOTDIR cannot be resolved without executing a profile: '+str(initial))
            chosen = absolute(core, value)
        if explicit and chosen != absolute(core, explicit):
            raise core.Failure('Exported ZDOTDIR disagrees with '+str(initial))
    return chosen


def roots(core):
    home = absolute(core, Path.home())
    config = absolute(core, os.environ.get('XDG_CONFIG_HOME') or home/'.config')
    data = absolute(core, os.environ.get('XDG_DATA_HOME') or home/'.local/share')
    # Resolve profile-specific configuration only if integration is necessary.
    zsh = absolute(core, os.environ.get('ZDOTDIR') or home)
    if os.name == 'nt':
        # Read Windows' actual redirected Documents location without launching
        # PowerShell (which could create caches even during dry-run).
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                documents = os.path.expandvars(winreg.QueryValueEx(key,'Personal')[0])
        except (ImportError, OSError):
            documents = str(home/'Documents')
        ps = absolute(core,documents)/'PowerShell'
        modules = ps/'Modules'
    else:
        ps = config/'powershell'
        modules = data/'powershell/Modules'
    return {k:str(v) for k,v in dict(home=home,config=config,data=data,zsh=zsh,ps=ps,modules=modules).items()}


def allowed(roots):
    h,c,d,z,p,m = (Path(roots[k]) for k in ('home','config','data','zsh','ps','modules'))
    return {
        'bashrc':h/'.bashrc', 'bashlogin':h/'.bash_profile',
        'bashlogin_alt':h/'.bash_login', 'profile':h/'.profile',
        'zshenv':z/'.zshenv', 'zshrc':z/'.zshrc',
        'fish':c/'fish/config.fish', 'powershell':p/'profile.ps1',
        'fish_dropin':c/'fish/conf.d/blastoff.fish',
        'fish_completion':c/'fish/completions/blastoff.fish',
        'bash_completion':d/'bash-completion/completions/blastoff',
        'ps_module':m/'blastoff/blastoff.psd1',
    }


def validate(core, record):
    if not record:
        return
    if not isinstance(record,dict) or not isinstance(record.get('roots'),dict):
        raise core.Failure('Invalid integration ownership record')
    if set(record['roots']) != {'home','config','data','zsh','ps','modules'}:
        raise core.Failure('Invalid integration roots')
    for value in record['roots'].values(): absolute(core,value)
    if Path(record['roots']['home']) != Path.home():
        raise core.Failure('Integration belongs to a different home; refusing profile changes')
    locations = allowed(record['roots'])
    for kind, item in record.get('profiles',{}).items():
        if kind not in locations or item.get('path') != str(locations[kind]):
            raise core.Failure('Unsafe profile ownership path')
        for block in item.get('blocks',[]):
            raw = base64.b64decode(block['bytes'],validate=True)
            if not raw or block['position'] not in ('prepend','append'):
                raise core.Failure('Invalid profile block record')
    for kind, item in record.get('files',{}).items():
        if kind not in ('fish_completion','fish_dropin','bash_completion','ps_module') or item.get('path') != str(locations[kind]):
            raise core.Failure('Unsafe external integration file path')
        if not re.fullmatch('[0-9a-f]{64}',item.get('sha256','')):
            raise core.Failure('Invalid integration file checksum')


def encoding(data):
    if data.startswith(b'\xff\xfe'): return 'utf-16-le', b'\xff\xfe'
    if data.startswith(b'\xfe\xff'): return 'utf-16-be', b'\xfe\xff'
    if data.startswith(b'\xef\xbb\xbf'): return 'utf-8', b'\xef\xbb\xbf'
    return 'utf-8', b''


def remove_blocks(core, data, item):
    for block in item.get('blocks',[]):
        raw = base64.b64decode(block['bytes'],validate=True)
        count = data.count(raw)
        if count == 1:
            data = data.replace(raw,b'',1)
        elif count > 1:
            raise core.Failure('Duplicated owned profile block: '+item['path'])
        else:
            codec,_ = encoding(data)
            if '# >>> blastoff ' in data.decode(codec):
                raise core.Failure('Modified owned integration in '+item['path']+'; preserve/review it before retrying')
            # Already manually removed blocks are not recreated on uninstall.
    return data


def profile(core, path, kind, bodies, previous, token):
    inspect(core,path)
    current = core.read(path) if core.exists(path) else b''
    clean = remove_blocks(core,current,previous) if previous else current
    codec,bom = encoding(clean)
    text = clean[len(bom):].decode(codec)
    if '# >>> blastoff ' in text or '# <<< blastoff ' in text:
        raise core.Failure('Unowned/modified Blastoff marker in '+str(path))
    newline = '\r\n' if '\r\n' in text else '\n'
    data = clean
    blocks = []
    for position, body in bodies:
        block = '# >>> blastoff '+token+' '+kind+' '+position+' >>>'+newline
        block += body.replace('\n',newline)+newline+'# <<< blastoff '+token+' '+kind+' '+position+' <<<'+newline
        raw = block.encode(codec)
        if position == 'prepend':
            offset = len(bom)
            if data[offset:].startswith('#!'.encode(codec)):
                at = data.find(newline.encode(codec),offset)
                if at < 0:
                    raise core.Failure('Profile shebang has no newline: '+str(path))
                offset = at+len(newline.encode(codec))
            data = data[:offset]+raw+data[offset:]
        else:
            if data and not data.endswith(newline.encode(codec)):
                raw = newline.encode(codec)+raw
            data += raw
        blocks.append({'position':position,'bytes':base64.b64encode(raw).decode('ascii')})
    return data, {'path':str(path),'created':previous.get('created',False) if previous else not core.exists(path), 'blocks':blocks}


def psquote(value): return "'"+str(value).replace("'","''")+"'"
def fishquote(value): return "'"+str(value).replace('\\','\\\\').replace("'","\\'")+"'"


def environment(prefix):
    binpath, manpath = shlex.quote(str(prefix/'bin')), shlex.quote(str(prefix/'share/man'))
    return f'''# Add only a leading entry; retain the caller's original search lists.
case "${{PATH-}}" in {binpath}|{binpath}:*) ;; *) PATH={binpath}${{PATH:+:$PATH}} ;; esac
case "${{MANPATH-}}" in {manpath}:*) ;; *) MANPATH={manpath}:${{MANPATH-}} ;; esac
case "$MANPATH" in *:) ;; *) MANPATH="$MANPATH:" ;; esac
export PATH MANPATH'''


def shell_prefix(name):
    executable = shutil.which(name)
    return Path(executable).resolve().parent.parent if executable else None


def plan(core, prefix, version_root, old, action, enabled=True):
    """Return file/profile edits; never execute a shell or create state here."""
    validate(core, old)
    files, profiles, notes, activation = {}, {}, [], []
    if action == 'uninstall':
        for item in (old or {}).get('profiles', {}).values():
            path = Path(item['path']); inspect(core, path)
            if core.exists(path):
                data = remove_blocks(core, core.read(path), item)
                profiles[path] = None if item.get('created') and not data else data
        return files, profiles, None, notes, activation
    if not enabled and not old:
        return files, profiles, None, ['Legacy entry point: discovery/profile activation remains manual.'], activation
    source_root = Path(core.__file__).resolve().parent.parent
    r = roots(core)
    record = {'roots': r, 'profiles': {}, 'files': {}}
    previous = (old or {}).get('profiles', {})
    token = hashlib.sha256(str(prefix).encode()).hexdigest()[:16]
    shared = prefix/'share/blastoff/integration'

    def add_profile(kind, bodies):
        locations = allowed(r)
        path = locations[kind]
        try:
            data, item = profile(core, path, kind, bodies, previous.get(kind), token)
        except core.Failure as error:
            instructions = '; '.join(body for _, body in bodies)
            raise core.Failure(str(error)+'; required setup: '+instructions+
                               '; then retry bash install.sh --prefix '+shlex.quote(str(prefix))) from error
        profiles[path] = data
        record['profiles'][kind] = item

    def owned(kind, data):
        path = allowed(r)[kind]
        files[path] = (data, 0o644)
        record['files'][kind] = {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}

    def payload(path, text):
        files[path] = (text.encode(), 0o644)

    # Inherited PATH is evidence for a fresh shell using the same environment,
    # not proof about unexported aliases/functions in an existing parent shell.
    path_ready = str(prefix/'bin') in os.environ.get('PATH', '').split(os.pathsep)
    native_man = shell_prefix('man') == prefix
    man_ready = native_man or str(prefix/'share/man') in os.environ.get('MANPATH', '').split(os.pathsep)
    if os.name != 'nt':
        if any(c in str(prefix) for c in ':\r\n'):
            raise core.Failure('POSIX prefix cannot contain colon/newline (PATH/MANPATH separators)')
        env = environment(prefix) if not path_ready or not man_ready else ''
        # Retain already-managed hooks even if their prior execution made the
        # current environment discoverable. Removing them would break next login.
        if shutil.which('bash'):
            framework = shell_prefix('bash')/'share/bash-completion/bash_completion'
            native = framework.is_file() and shell_prefix('bash') == prefix
            # bash-completion 2.12+ also searches the resolved command's prefix.
            # Inspect the installed framework, never execute it during planning.
            relative_loader = framework.is_file() and b'${dir%/*}/share/bash-completion/completions/' in core.read(framework, links=True)
            discoverable = native or relative_loader
            body = env
            if not discoverable:
                owned('bash_completion', core.read(source_root/'completions/blastoff.bash'))
                body += '\ncase $- in *i*) . '+shlex.quote(str(prefix/'share/bash-completion/completions/blastoff'))+' ;; esac'
            if body or any(k in previous for k in ('bashrc', 'bashlogin', 'bashlogin_alt', 'profile')):
                payload(shared/'bash.sh', environment(prefix)+'\n'+
                        'case $- in *i*) . '+shlex.quote(str(prefix/'share/bash-completion/completions/blastoff'))+' ;; esac\n')
                line = '. '+shlex.quote(str(shared/'bash.sh'))
                add_profile('bashrc', [('append', line)])
                locations = allowed(r)
                login = next((k for k in ('bashlogin', 'bashlogin_alt', 'profile') if core.exists(locations[k])), 'bashlogin')
                add_profile(login, [('append', line)])
                activation.append('Bash: '+line)
        if shutil.which('zsh'):
            native = shell_prefix('zsh') == prefix
            configured = str(prefix/'share/zsh/site-functions') in os.environ.get('FPATH', '').split(os.pathsep)
            # Termux Zsh does not include site-functions in its compiled fpath.
            # Supply an owned copy in its existing autoload directory as well as
            # the public canonical site-functions location; no profile needed.
            bridge = prefix/'share/zsh/functions/Completion/Unix'
            if native and bridge.is_dir():
                files[bridge/'_blastoff'] = (core.read(source_root/'completions/blastoff.zsh'), 0o644)
                notes.append('Zsh native autoload discovery: '+str(bridge/'_blastoff'))
            else:
                native = False
            if env or not (native or configured) or 'zshrc' in previous or 'zshenv' in previous:
                r['zsh'] = str(zsh_root(core, Path(r['home']), Path(r['config'])))
                early = environment(prefix)+'\n_blastoff_fpath='+shlex.quote(str(prefix/'share/zsh/site-functions'))+"\nif (( ! ${fpath[(Ie)$_blastoff_fpath]} )); then fpath=(\"$_blastoff_fpath\" $fpath); fi\nunset _blastoff_fpath\n"
                payload(shared/'zsh-early.zsh', early)
                payload(shared/'zsh.zsh', early+"if [[ -o interactive ]]; then\n  if (( ! $+functions[compdef] )); then autoload -Uz compinit; compinit -D; fi\n  autoload -Uz _blastoff\n  compdef _blastoff blastoff\nfi\n")
                add_profile('zshenv', [('append', '. '+shlex.quote(str(shared/'zsh-early.zsh')))])
                add_profile('zshrc', [('prepend', '. '+shlex.quote(str(shared/'zsh-early.zsh'))),
                                      ('append', '. '+shlex.quote(str(shared/'zsh.zsh')))])
                activation.append('Zsh: source '+shlex.quote(str(shared/'zsh.zsh')))
        if shutil.which('fish'):
            native = shell_prefix('fish') == prefix
            if not native:
                owned('fish_completion', core.read(source_root/'completions/blastoff.fish'))
            if env or 'fish_dropin' in (old or {}).get('files', {}):
                b, m = fishquote(prefix/'bin'), fishquote(prefix/'share/man')
                text = (f'if not set -q PATH[1]; or test "$PATH[1]" != {b}\n    set -gx PATH {b} $PATH\nend\n'
                        f'if not set -q MANPATH[1]; or test "$MANPATH[1]" != {m}\n    set -gx MANPATH {m} $MANPATH\nend\n'
                        "if not contains -- '' $MANPATH\n    set -gx MANPATH $MANPATH ''\nend\n")
                owned('fish_dropin', text.encode())
        notes.append('Fresh shells use the installed paths; existing shells may need hash -r (Bash) or rehash (Zsh).')
    ps_profile = allowed(r)['powershell']
    independent_ps = False
    if core.exists(ps_profile) and 'powershell' not in previous:
        inspect(core, ps_profile)
        data = core.read(ps_profile); codec,bom = encoding(data)
        independent_ps = '# >>> blastoff powershell-currentuser ' in data[len(bom):].decode(codec)
    if independent_ps:
        notes.append('Independent CurrentUser PowerShell integration retained; shell installer does not own it.')
    elif shutil.which('pwsh'):
        manifest = version_root/'powershell/blastoff.psd1'
        body = 'Import-Module '+psquote(manifest)+' -Global\n'
        payload(shared/'powershell.ps1', body)
        add_profile('powershell', [('append', '. '+psquote(shared/'powershell.ps1'))])
        activation.append('PowerShell: '+body.strip())
    else:
        notes.append('PowerShell engine unavailable; module shipped, native Windows verification deferred.')
    if old:
        if old['roots'] != r:
            raise core.Failure('Integration roots changed; uninstall with the original roots before moving integration')
        # A temporarily absent shell must not lose ownership of its hooks.
        for kind, item in old.get('profiles', {}).items():
            record['profiles'].setdefault(kind, item)
        for kind, item in old.get('files', {}).items():
            record['files'].setdefault(kind, item)
    return files, profiles, record, notes, activation
