"""Prepare small native environment adapters without persisting caller values."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from environment import declarations, TOKEN, TOOL_PATHS
from file_platform import lock, open_nofollow
from profiles import resolve, SENSITIVE
import mise_shims

LIB=Path(__file__).resolve().parent


def quote(value, shell):
    return "'"+value.replace("'","''")+"'" if shell=='powershell' else "'"+value.replace('\\','\\\\').replace("'","\\'")+"'"


def expression(template, shell):
    pieces=[];cursor=0
    for match in TOKEN.finditer(template):
        pieces.append(quote(template[cursor:match.start()],shell))
        pieces.append(('$(if ($env:HOME) { $env:HOME } else { $HOME })' if match[1]=='HOME' else '$env:'+match[1]) if shell=='powershell' else '"$'+match[1]+'"')
        cursor=match.end()
    pieces.append(quote(template[cursor:],shell))
    return '('+' + '.join(pieces)+')' if shell=='powershell' else ''.join(pieces)


def generate(root,shell, metadata=None):
    profile=resolve(root)
    from profile_environment import Model
    generated = Model(root, profile)
    shim_inputs = []
    context, shim_guard = mise_shims.startup_context(root, profile, generated.scalars)
    shim = mise_shims.resolve(context, profile['facts']['platform'] == 'windows', shim_inputs)
    paths=[LIB/'native_startup.py',LIB/'profile_config.py',LIB/'shell/settings.tsv',LIB/'profiles.py',LIB/'platform_info.py',LIB/'environment.py',LIB/'shell/environment.json']
    from style_config import Styles
    styles = Styles(root, profile)
    paths.extend(styles.startup_inputs())
    paths.extend(Path(row['root'])/'profile.json' for row in profile['layers'])
    for p in (root/'profiles', *[root/'profiles'/p for p in ('termux','linux','wsl','windows')]):
        if p.exists():paths.append(p)
        if (p/'distros').is_dir():
            paths.append(p/'distros');paths.extend(c for c in (p/'distros').iterdir() if c.is_dir())
    paths.extend(generated.inputs)
    shim_adapter = LIB/'shell'/('mise-path.ps1' if shell == 'powershell' else 'mise-path.fish')
    paths.extend((LIB/'mise_shims.py', shim_adapter))
    paths.extend(path for path in shim_inputs if path.exists())
    missing = [path for path in shim_inputs if not path.exists()]
    if shell == 'powershell':
        from files.file_platform import state_root
        palette = state_root()/'current/theme/palette.json'
        if not palette.exists():
            missing.append(palette)
        # startup_inputs already watches existing preference files and directories.
        missing.extend(sorted({p.parent for p in styles.preference_inputs() if not p.parent.exists()}))
    paths = list(dict.fromkeys(paths))
    if Path('/etc/os-release').exists():paths.append(Path('/etc/os-release'))
    if metadata is not None:
        metadata.extend(dict(path=str(p),size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in paths)
    def q(value):return quote(str(value),shell)
    from profile_config import settings as profile_settings
    options = profile_settings(root, profile)
    config_path = str(Path(profile['layers'][-1]['root']) / 'config.json') if profile['layers'] else ''
    facts=profile['facts']
    identity=dict(DOTS_PLATFORM=facts['platform'],DOTS_DISTRO=facts['distro'],DOTS_ARCH=facts['architecture'],DOTS_RUNTIME=facts['runtime'],DOTS_PROFILE=profile['current'],DOTS_PROFILE_LAYERS=' '.join(r['id'] for r in profile['layers']),DOTS_PROFILE_CHECKOUT=str(root),DOTS_PROFILE_BIN_PATHS=os.pathsep.join(str(Path(r['root'])/'bin') for r in reversed(profile['layers'])))
    if shell=='powershell':
        lines=["if ($env:DOTS -cne "+q(root)+") { return $false }"]
        for path in paths:
            stat=path.lstat() if path in shim_inputs and path.is_symlink() else path.stat()
            # Python epoch seconds -> .NET ticks. Milliseconds avoid filesystem
            # precision conversion differences while detecting normal changes.
            milliseconds=stat.st_mtime_ns//1_000_000
            lines.append("$item = Get-Item -LiteralPath "+q(path)+" -Force -ErrorAction SilentlyContinue")
            lines.append("if (-not $item -or [math]::Floor(($item.LastWriteTimeUtc.Ticks - 621355968000000000) / 10000) -ne "+str(milliseconds)+") { return $false }")
        for path in missing:
            lines.append("if (Test-Path -LiteralPath "+q(path)+") { return $false }")
        for key, values in shim_guard.items():
            lines.append("if (" + ' -and '.join("[string]$env:"+key+" -cne "+q(v) for v in values) + ") { return $false }")
        for key in ('TERMUX_VERSION','TERMUX__PREFIX','PREFIX','WSL_DISTRO_NAME','WSL_INTEROP','OS'):
            lines.append("if ([string]$env:"+key+" -cne "+q(os.environ.get(key,''))+") { return $false }")
        lines += ["$global:DotsProfileSettings = @{}", "$global:DotsProfileSettingOrigins = @{}", "$global:DotsProfileConfigPath = "+q(config_path)]
        from completion_preferences import rows as completion_rows
        lines.append('$global:DotsCompletionStyles = @{}')
        for key, value, kind in completion_rows(styles=styles):
            if key == '__completion.enabled' or kind == 'style':
                lines.append('$global:DotsCompletionStyles['+q(key.rsplit('.', 1)[1])+'] = '+q(value))
        lines.append('$global:DotsProfileShellDirs = @(' + ','.join(q(Path(row['root'])/'shells') for row in profile['layers']) + ')')
        for key, row in options.items():
            if key == 'files.backup': continue
            lines += ["$global:DotsProfileSettings["+q(key)+"] = "+q(row['value']), "$global:DotsProfileSettingOrigins["+q(key)+"] = "+q(row['source'])]
        lines += ["if (-not $global:DotsEnvironmentApplied) { $global:DotsEnvironmentApplied = @{} }",r'''function Set-DotsEnvironmentDefault([string]$Name, [string]$Value) {
    $current = [Environment]::GetEnvironmentVariable($Name)
    if ($Name -ceq 'LESS' -and $Value -ceq '--mouse' -and $current -and $current -cnotmatch '(^|\s)--(mouse|MOUSE)([=\s]|$)') {
        $current = '--mouse ' + $current
        [Environment]::SetEnvironmentVariable($Name, $current, 'Process')
    }
    if (-not $current -or ($global:DotsEnvironmentApplied.ContainsKey($Name) -and $current -ceq $global:DotsEnvironmentApplied[$Name])) {
        [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
        $global:DotsEnvironmentApplied[$Name] = $Value
    }
}''']
        lines += generated.shell(shell).splitlines()
        for key,(value,_) in declarations(root,profile).items():
            if SENSITIVE.search(key) and value and not TOKEN.fullmatch(value): raise ValueError('sensitive defaults must reference an environment variable')
            if value=='@editor':
                lines.append("$editor = Get-Command nvim,vim,vi,code,nano -ErrorAction SilentlyContinue | Select-Object -First 1")
                expr="$(if ($editor) { $editor.Name } else { 'vi' })"
            else:expr=expression(value,shell)
            lines.append('Set-DotsEnvironmentDefault '+q(key)+' '+expr)
        lines.append("$toolPaths = @($env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator))")
        for placement, variable, suffix in TOOL_PATHS:
            base = "$(if ($env:HOME) { $env:HOME } else { $HOME })" if variable == 'HOME' else "$env:" + variable
            path = f"(Join-Path {base} {q(suffix)})" if suffix else base
            operation = "@($directory) + $toolPaths" if placement == 'prepend' else "$toolPaths + @($directory)"
            lines += [f"if ({base}) {{", f"  $directory = {path}",
                      f"  if ($toolPaths -notcontains $directory -and (Test-Path -LiteralPath $directory -PathType Container)) {{ $toolPaths = {operation} }}", "}"]
        lines.append("$env:PATH = $toolPaths -join [IO.Path]::PathSeparator")
        lines.append("$previousProfilePaths = @($env:DOTS_PROFILE_PATHS -split [regex]::Escape([string][IO.Path]::PathSeparator))")
        lines.extend('$env:'+key+' = '+q(value) for key,value in identity.items())
        paths=[str(Path(row['root'])/p) for row in reversed(profile['layers']) for p in row.get('path',['bin','scripts'])]
        lines.append("$profilePaths = @("+','.join(map(q,paths))+")")
        if shim:
            lines.append('$shim = '+q(shim))
            lines.append(shim_adapter.read_text(encoding='utf-8'))
        lines += ["$entries = @($profilePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Container }) + @($env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator) | Where-Object { $previousProfilePaths -cnotcontains $_ })", "$env:DOTS_PROFILE_PATHS = (@($profilePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Container }) -join [IO.Path]::PathSeparator)", "$env:PATH = (@($entries | Select-Object -Unique) -join [IO.Path]::PathSeparator)", 'return $true']
    else:
        signature=subprocess.check_output(['stat','-c','%d:%i:%s:%y:%z','--',*map(str,paths)],text=True).rstrip('\n')
        lines=['test "$DOTS" = '+q(root)+'; or return 1', 'set -l signature (command stat -c '+q('%d:%i:%s:%y:%z')+' -- '+' '.join(map(q,paths))+' 2>/dev/null | string collect)', 'test "$signature" = '+q(signature)+'; or return 1']
        for path in missing:
            lines.append('test ! -e '+q(path)+'; or return 1')
        for key, values in shim_guard.items():
            lines.append('contains -- "$'+key+'" '+' '.join(map(q,values))+'; or return 1')
        for key in ('TERMUX_VERSION','TERMUX__PREFIX','PREFIX','WSL_DISTRO_NAME','WSL_INTEROP','OS'):
            lines.append('test "$'+key+'" = '+q(os.environ.get(key,''))+'; or return 1')
        lines += ['set -g _dots_profile_setting_keys', 'set -g _dots_profile_config_path '+q(config_path)]
        lines.append('set -g _dots_profile_shell_dirs ' + ' '.join(q(Path(row['root'])/'shells') for row in profile['layers']))
        for key, row in options.items():
            if key == 'files.backup': continue
            lines += ['set -a _dots_profile_setting_keys '+q(key), 'set -g _dots_profile_setting_'+key+' '+q(row['value']), 'set -g _dots_profile_source_'+key+' '+q(row['source'])]
        lines += generated.shell(shell).splitlines()
        for key,(value,_) in declarations(root,profile).items():
            if SENSITIVE.search(key) and value and not TOKEN.fullmatch(value): raise ValueError('sensitive defaults must reference an environment variable')
            if value=='@editor':
                lines += ['set -l editor vi','for candidate in nvim vim vi code nano','  if command -q $candidate; set editor $candidate; break; end','end'];expr='$editor'
            else:expr=expression(value,shell)
            if key == 'LESS' and value == '--mouse':
                lines += ['if test -n "$LESS"; and not string match -rq '+q(r'(^|\s)--(mouse|MOUSE)([=\s]|$)')+' -- "$LESS"',
                          '  set -gx LESS "--mouse $LESS"', 'end']
            lines += ['if not set -q '+key+'; or test -z "$'+key+'"; or test "$'+key+'" = "$_dots_applied_'+key+'"', '  set -gx '+key+' '+expr, '  set -g _dots_applied_'+key+' "$'+key+'"', 'end']
        for placement, variable, suffix in TOOL_PATHS:
            path = f'"${variable}' + ('/' + suffix if suffix else '') + '"'
            flag = '-p' if placement == 'prepend' else '-a'
            lines += [f'if test -n "${variable}"; and test -d {path}; and not contains -- {path} $PATH',
                      f'  set -gx {flag} PATH {path}', 'end']
        lines.extend('set -gx '+key+' '+q(value) for key,value in identity.items())
        paths=[str(Path(row['root'])/p) for row in reversed(profile['layers']) for p in row.get('path',['bin','scripts'])]
        lines += ['set -l previous_profile_paths (string split : -- "$DOTS_PROFILE_PATHS")', 'set -l profile_paths']
        for path in paths:lines.append('if test -d '+q(path)+'; set -a profile_paths '+q(path)+'; end')
        lines.append('set -l shim '+q(str(shim) if shim else ''))
        lines.append(shim_adapter.read_text(encoding='utf-8'))
        lines += ['set -l clean_path $profile_paths','for entry in $inherited_path', '  contains -- "$entry" $previous_profile_paths; and continue','  contains -- "$entry" $clean_path; or set -a clean_path "$entry"','end', 'set -gx DOTS_PROFILE_PATHS (string join : -- $profile_paths)','set -gx PATH $clean_path','return 0']
    return '\n'.join(lines)+'\n'


def replace_cache_file(source, target):
    # Windows readers can open a script without sharing delete access. Keep
    # the existing complete cache available while waiting for the handle.
    delays = iter((0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.4))
    while True:
        try:
            os.replace(source, target)
            return
        except PermissionError as error:
            delay = next(delays, None)
            if delay is None or os.name != 'nt' or getattr(error, 'winerror', None) not in (5, 32, 33):
                raise
            time.sleep(delay)


def prepare(root,shell,target):
    inputs=[]
    body=generate(root,shell,inputs)
    # Windows PowerShell 5.1 decodes BOM-less scripts using the ANSI code page.
    # Keep literal Unicode checkout paths valid when it dot-sources this cache.
    data=body.encode('utf-8-sig' if shell=='powershell' else 'utf-8')
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix='.environment-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        fd, manifest = tempfile.mkstemp(prefix='.metadata-', dir=target.parent)
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(dict(version=1,root=str(root),shell=shell,inputs=inputs,digest=hashlib.sha256(data).hexdigest()),stream)
                stream.flush();os.fsync(stream.fileno())
            # Each cold writer publishes its script and matching diagnostic
            # manifest together. Readers still use the existing atomic rename.
            lock_path = target.with_suffix(target.suffix + '.lock')
            with os.fdopen(open_nofollow(lock_path, os.O_CREAT | os.O_RDWR), 'r+b') as writer:
                lock(writer, blocking=True)
                replace_cache_file(name, target)
                replace_cache_file(manifest, target.with_suffix(target.suffix+'.json'))
        finally:
            Path(manifest).unlink(missing_ok=True)
    finally:
        if os.path.exists(name):os.unlink(name)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shell',choices=('powershell','fish'));parser.add_argument('target',type=Path)
    args=parser.parse_args()
    prepare(Path(os.environ.get('DOTS') or LIB.parents[1]).resolve(),args.shell,args.target)
