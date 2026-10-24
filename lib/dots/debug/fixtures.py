"""Runtime-owned disposable fixtures; never import or run personal startup files."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def copy_tree(source, target, root, checkout):
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in ('__pycache__','.git') or item.suffix == '.pyc': continue
        dest=target/item.name
        if item.is_symlink():
            resolved=item.resolve()
            if not resolved.is_relative_to(root): raise ValueError('fixture input escapes public checkout')
            if os.name=='nt':
                if resolved.is_dir(): copy_tree(resolved,dest,root,checkout)
                else: shutil.copy2(resolved,dest)
            else: dest.symlink_to(os.path.relpath(checkout/resolved.relative_to(root),dest.parent), target_is_directory=resolved.is_dir())
        elif item.is_dir(): copy_tree(item,dest,root,checkout)
        elif item.is_file(): shutil.copy2(item,dest)


@contextmanager
def fixture(root):
    with tempfile.TemporaryDirectory(prefix='dots-debug-') as name:
        base=Path(name); home=base/'home'; home.mkdir(); checkout=home/'checkout space'; checkout.mkdir()
        for relative in ('lib/dots','shells/shared','shells/bash','shells/zsh'):
            copy_tree(root/relative,checkout/relative,root,checkout)
        # Native PowerShell fixtures include only public first-party entry files.
        ps=checkout/'shells/powershell';ps.mkdir(parents=True)
        for source in (root/'shells/powershell').glob('*.ps1'): shutil.copy2(source,ps/source.name)
        for relative in ('shells/environment.sh','bin/dots','bin/dots.ps1','bin/lib/common.sh'):
            target=checkout/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/relative,target)
        for platform in ('termux','linux','wsl','windows'):
            p=checkout/'profiles'/platform;p.mkdir(parents=True)
            (p/'profile.json').write_text(json.dumps(dict(schema=1,id=platform)))
        (checkout/'.dots').mkdir();(checkout/'.dots/sources.json').write_text('{"schema":1,"sources":[]}')
        tools=base/'commands';tools.mkdir()
        names=('bash','zsh','sh','pwsh','powershell','python3','stat','dirname','readlink','uname','mkdir','cat','date','sleep','tr','sed','sort','cut','head','tail','locale','wc','rm','mv','chmod','touch','cksum','mktemp')
        for name in names:
            executable=shutil.which(name)
            if executable and os.name!='nt': (tools/name).symlink_to(executable)
        env={k:v for k,v in os.environ.items() if k in ('PREFIX','TERMUX__PREFIX','TERMUX_VERSION','SystemRoot','SYSTEMROOT','WINDIR','COMSPEC','OS')}
        env.update(HOME=str(home),USERPROFILE=str(home),DOTS=str(checkout),PATH=str(tools),TMPDIR=str(base),TEMP=str(base),TMP=str(base),
                   XDG_CONFIG_HOME=str(home/'config'),XDG_CACHE_HOME=str(home/'cache'),XDG_STATE_HOME=str(home/'state'),XDG_DATA_HOME=str(home/'data'),
                   APPDATA=str(home/'config'),LOCALAPPDATA=str(home/'data'),DOTS_INIT_THEME='0',DOTS_INIT_COMPLETION='0',DOTS_TERMUX_AUTOSTART='0',DOTS_ZSH_SUGGESTIONS='none',TERM='xterm-256color')
        if os.name=='nt':
            # Only the current Python directory and Windows system utilities.
            native_shell=shutil.which('pwsh') or shutil.which('powershell')
            native_paths=[str(Path(sys.executable).parent),str(Path(os.environ['SystemRoot'])/'System32')]
            if native_shell: native_paths.append(str(Path(native_shell).parent))
            env['PATH']=os.pathsep.join(native_paths)
        for key in ('XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_DATA_HOME','APPDATA','LOCALAPPDATA'): Path(env[key]).mkdir(parents=True,exist_ok=True)
        if os.name!='nt':
            for filename,relative in (('.zshenv','shells/zsh/zshenv'),('.zshrc','shells/zsh/zshrc'),('.bashrc','shells/bash/.bashrc')):
                (home/filename).symlink_to(checkout/relative)
            (home/'.bash_profile').write_text('source "$HOME/.bashrc"\n')
        yield checkout,env,base
