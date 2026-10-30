"""Generated profile paths and native maps; never execute profile files."""
import json
import re
import shlex
from pathlib import Path
from profiles import available, resolve, definition, directory

STANDARD = ('config', 'bin', 'scripts', 'lib', 'fonts', 'shells', 'docs', 'skills')
APPLICATIONS = json.loads((Path(__file__).parent/'shell/environment.json').read_text())
IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_]*\Z')
RESERVED = set(('HOME PATH SHELL SHELLS DOCS DOTS DOTBIN DOTSCRIPTS DOTFILES DOTCONFIG '
                'DOTSHHHH ZSH PWSH DOTHEMES THEMES PWD OLDPWD USER USERPROFILE APPDATA '
                'LOCALAPPDATA TEMP TMP TMPDIR PREFIX TERMUX__PREFIX OS TERM IFS ENV '
                'BASH_ENV CDPATH FPATH HISTFILE HISTSIZE FIGNORE EDITOR VISUAL LESS '
                'XDG_CONFIG_HOME XDG_DATA_HOME XDG_CACHE_HOME XDG_STATE_HOME BASHOPTS SHELLOPTS '
                'UID EUID PPID GROUPS RANDOM SECONDS LINENO FUNCNAME BASH_VERSION BASH_VERSINFO '
                'BASH_SOURCE BASH_LINENO BASH_ARGC BASH_ARGV BASH_CMDS BASH_ALIASES DIRSTACK '
                'ZSH_VERSION ZSH_EVAL_CONTEXT ZSH_NAME ZSH_SUBSHELL EPOCHSECONDS EPOCHREALTIME ESC RST').split())
RESERVED.update(APPLICATIONS['defaults'])
RESERVED.update(key.upper() for key in APPLICATIONS['observed'])
RESERVED_MAPS = set(('dot shells zsh path status options commands functions aliases '
                     'env home profile dotsprofile pipestatus argv args null true false '
                     'error host executioncontext input matches lastexitcode pshome pid psversiontable '
                     'psedition psdebugcontext psscriptroot pscommandpath myinvocation nestedpromptlevel '
                     'psboundparameters psstyle foreach switch stacktrace profile_map '
                     'parameters terminfo fpath cdpath manpath modules reswords signals history '
                     'dotsgeneratedpaths dotsgeneratedmaps dotsenvironmentapplied dotsprofileconfigpath '
                     'dotsprofilesettingorigins dotsprofilesettings dots_colors dots_option_sources '
                     'dots_options dots_palette dots_roles esc rst black red green yellow blue magenta '
                     'cyan white bright_black bright_red bright_green bright_yellow bright_blue '
                     'bright_magenta bright_cyan bright_white').split())


def normalized(value):
    return re.sub('[^a-zA-Z0-9_]', '_', value).lower()


class Model:
    def __init__(self, root, selected=None, overrides=None):
        self.root = Path(root).resolve()
        selected = resolve(self.root) if selected is None else selected
        overrides = overrides or {}
        rows = [definition(self.root, row['id'], overrides[row['id']]) if row['id'] in overrides else row
                for row in available(self.root)]
        self.scalars, self.maps, self.origins, self.inputs = {}, {}, {}, [Path(__file__)]
        self.scalar('DOTFONTS', str(self.root/'fonts'), 'shared')
        self.inputs += [self.root/'profiles' if (self.root/'profiles').is_dir() else self.root]
        for platform in ('termux','linux','wsl','windows'):
            for path in (self.root/'profiles'/platform, self.root/'profiles'/platform/'distros'):
                if path.is_dir(): self.inputs.append(path)
        for row in rows:
            path = Path(row['root'])
            self.inputs += [path, path/'profile.json']
            paths = dict(root=str(path), **{key: str(path/key) for key in STANDARD})
            paths['configs'] = paths['config']
            for child in sorted(path.iterdir()):
                if child.name.startswith('.') or not child.is_dir(): continue
                key = normalized(child.name)
                if key in paths and paths[key] != str(child):
                    # A historical configs symlink is the same logical directory.
                    if key == 'configs' and child.resolve() == (path/'config').resolve(): continue
                    raise ValueError('profile directory name collision: '+child.name)
                paths[key] = str(child)
            name = normalized(row['id'])
            self.namespace('DOTS'+name.upper(), name, paths, row['id'])
            alias = row.get('alias')
            if alias: self.namespace(alias.upper(), alias.lower(), paths, row['id'])
        active = next((row for row in rows if row['id'] == selected['current']), None)
        paths = (self.maps[normalized(active['id'])] if active else
                 dict(root=str(directory(self.root,selected['current'])), **{
                     key:str(directory(self.root,selected['current'])/key) for key in STANDARD}))
        paths = dict(paths, configs=paths['config'])
        self.namespace('PROFILE', 'profile', paths, selected['current'], active=True)
        # Compatibility is generated centrally, including inactive platform paths.
        bridges = {'termux': {'DROIDBIN':'bin','DROIDCONFIGS':'config','DROIDSHELLS':'shells',
                             'DROIDZSH':'shells/zsh','DOTERMUX':'termux'},
                   'windows': {'WINDOTFILES':'config','WINDOWCONFIG':'config','RAINMETER':'rainmeter'}}
        for identity, names in bridges.items():
            row = next((r for r in rows if r['id'] == identity), None)
            if row is None: continue
            rootpath = Path(row['root'])
            for name, relative in names.items(): self.scalar(name, str(rootpath/relative), identity)
            legacy = dict(self.maps[identity])
            if identity == 'termux': legacy.update(zsh=str(rootpath/'shells/zsh'),termux=str(rootpath/'termux'))
            else: legacy.update(files=str(rootpath/'config'),rainmeter=str(rootpath/'rainmeter'))
            self.map('droid' if identity == 'termux' else 'windot', legacy)
        for row in rows:
            for name in row.get('environment', {}):
                if name in self.scalars or name.startswith(('PROFILE','DOTS')):
                    raise ValueError('environment cannot define backend-owned name: '+name)
        self.inputs = list(dict.fromkeys(self.inputs))

    def scalar(self, name, value, owner):
        if name in RESERVED or name.startswith('DOTS_') or name in self.scalars: raise ValueError('profile variable collision: '+name)
        self.scalars[name] = value
        self.origins[name] = 'profile:'+owner

    def map(self, name, paths, active=False):
        if name in self.maps or name in RESERVED_MAPS and not (active and name == 'profile'):
            raise ValueError('profile map collision: '+name)
        self.maps[name] = dict(paths)

    def namespace(self, prefix, name, paths, owner, active=False):
        self.map(name, paths, active)
        for key, value in paths.items():
            self.scalar(prefix + ('' if key == 'root' else key.upper()), value, owner)

    def shell(self, shell):
        """Compile literal data. Cleanup uses private, non-exported ownership maps."""
        if shell in ('bash','zsh'):
            q = shlex.quote
            def associative(values):
                return '('+' '.join(('['+key+']='+q(value)) if shell=='bash' else key+' '+q(value)
                                    for key,value in values.items())+')'
            lines = ['typeset -gA _dots_generated_paths',
                     'for _dots_generated_name in "${!_dots_generated_paths[@]}"; do' if shell == 'bash' else 'for _dots_generated_name in "${(@k)_dots_generated_paths}"; do',
                     '  [[ -n $_dots_generated_name ]] || continue',
                     '  if [[ ${!_dots_generated_name-} == "${_dots_generated_paths[$_dots_generated_name]}" ]]; then unset "$_dots_generated_name"; fi' if shell == 'bash' else
                     '  if [[ ${(P)_dots_generated_name} == "${_dots_generated_paths[$_dots_generated_name]}" ]]; then unset "$_dots_generated_name"; fi',
                     'done', 'for _dots_generated_name in "${_dots_generated_maps[@]}"; do [[ -n $_dots_generated_name ]] && unset "$_dots_generated_name"; done',
                     '_dots_generated_paths='+associative(self.scalars), 'typeset -ga _dots_generated_maps',
                     '_dots_generated_maps=('+' '.join(self.maps)+')',
                     'export '+' '.join(name+'='+q(value) for name,value in self.scalars.items())]
            for name,paths in self.maps.items():
                lines += ['unset '+name, 'typeset -gA '+name, name+'='+associative(paths)]
            lines += ['unset _dots_generated_name', '_dots_profile_environment_ready=1']
        elif shell == 'powershell':
            def q(value): return "'"+value.replace("'","''")+"'"
            lines = ["if ($global:DotsGeneratedPaths) { foreach ($name in @($global:DotsGeneratedPaths.Keys)) { if ([Environment]::GetEnvironmentVariable($name) -ceq $global:DotsGeneratedPaths[$name]) { [Environment]::SetEnvironmentVariable($name, $null, 'Process') } } }",
                     "foreach ($name in $global:DotsGeneratedMaps) { Remove-Variable -Scope Global -Name $name -ErrorAction SilentlyContinue }",
                     '$global:DotsGeneratedPaths = @{}', '$global:DotsGeneratedMaps = @()']
            for name,value in self.scalars.items():
                lines += ['$env:'+name+' = '+q(value), '$global:DotsGeneratedPaths['+q(name)+'] = '+q(value)]
            for name,paths in self.maps.items():
                name = 'DotsProfile' if name == 'profile' else name
                lines += ['$global:'+name+' = @{'+ '; '.join(q(k)+' = '+q(v) for k,v in paths.items())+'}', '$global:DotsGeneratedMaps += '+q(name)]
        elif shell == 'fish':
            def q(value): return "'"+value.replace('\\','\\\\').replace("'","\\'")+"'"
            lines = ['for name in $_dots_generated_names; set -e $name; end', 'set -g _dots_generated_names']
            for name,value in self.scalars.items():
                lines += ['set -gx '+name+' '+q(value), 'set -a _dots_generated_names '+name]
            for name,paths in self.maps.items():
                for key,value in paths.items():
                    var = name+'_'+key
                    lines += ['set -g '+var+' '+q(value), 'set -a _dots_generated_names '+var]
        else: raise ValueError('unsupported profile environment renderer')
        return '\n'.join(lines)+'\n'
