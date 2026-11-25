# Xonsh supplies its Python runtime even before a checkout is present.
def _dots_rc_loader():
    from pathlib import Path
    import os
    import shutil
    session = __xonsh__.env
    home = Path(session.get('HOME') or session.get('USERPROFILE') or Path.home())
    def valid(root):
        launcher = root / 'bin' / ('dots.ps1' if os.name == 'nt' else 'dots')
        return (root.is_absolute() and launcher.is_file() and (os.name == 'nt' or os.access(launcher, os.X_OK))
                and (root / 'lib/dots/shell/startup.bash').is_file()
                and (root / 'shells/xonsh/init.xsh').is_file())

    root = Path(session.get('DOTS_BOOTSTRAP_DIR') or home / 'dots')
    data = home / '.local/share/dots/bootstrap'
    if not session.get('DOTS_BOOTSTRAP_DIR'):
        cli = shutil.which('dots.ps1' if os.name == 'nt' else 'dots', path=os.pathsep.join(session.get('PATH', [])))
        pin = data / 'checkout'
        if cli:
            root = Path(cli).resolve().parent.parent
        elif pin.is_file():
            try:
                root = Path(pin.read_text(encoding='utf-8').rstrip('\r\n'))
            except (OSError, UnicodeError, ValueError):
                pass
    if not valid(root):
        import subprocess
        env = session.detype()
        mode = 'interactive' if __xonsh__.env.get('XONSH_INTERACTIVE') else 'offline'
        if os.name == 'nt':
            argv = ['powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(data / 'locate.ps1'), mode, '-Utf8', '-Shell', 'xonsh']
        else:
            argv = ['sh', str(data / 'locate.sh'), mode, 'xonsh']
        result = subprocess.run(argv, stdout=subprocess.PIPE, encoding='utf-8' if os.name == 'nt' else None, text=True, env=env)
        if result.returncode or not result.stdout.strip():
            return None
        root = Path(result.stdout.rstrip('\r\n'))
        if not valid(root):
            return None
    return str(root / 'shells/xonsh/init.xsh')

_dots_rc_path = _dots_rc_loader()
if _dots_rc_path:
    source @(_dots_rc_path)
del _dots_rc_loader, _dots_rc_path
