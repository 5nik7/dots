"""Explicit clipboard writes through native platform capabilities."""
import os
import shutil
import subprocess

from platform_info import detect


def copy(text):
    platform = detect()['platform']
    if platform == 'termux':
        choices = [('termux-clipboard-set', [])]
    elif platform == 'windows':
        script = ('[Console]::InputEncoding = New-Object System.Text.UTF8Encoding; '
                  'Set-Clipboard -Value ([Console]::In.ReadToEnd())')
        choices = [(shell, ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script])
                   for shell in ('pwsh', 'powershell')]
    else:
        choices = []
        if os.environ.get('WAYLAND_DISPLAY'): choices.append(('wl-copy', []))
        if os.environ.get('DISPLAY'):
            choices += [('xclip', ['-selection', 'clipboard']), ('xsel', ['--clipboard', '--input'])]
    for tool, arguments in choices:
        executable = shutil.which(tool)
        if not executable: continue
        try:
            result = subprocess.run([executable, *arguments], input=text.encode('utf-8'),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
        except (OSError, subprocess.SubprocessError):
            raise ValueError('Clipboard write failed; use Print brief to export the text') from None
        if result.returncode:
            raise ValueError('Clipboard write failed; use Print brief to export the text')
        return
    raise ValueError('Clipboard unavailable; install the native clipboard tool or use Print brief')
