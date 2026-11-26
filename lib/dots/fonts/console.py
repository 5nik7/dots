"""Select a face only when a private Windows Console actually returns it."""
import hashlib
import json
import os
import subprocess
import sys


def probe(face):
    import ctypes
    from ctypes import wintypes

    class Coord(ctypes.Structure):
        _fields_ = [('x', wintypes.SHORT), ('y', wintypes.SHORT)]

    class ConsoleFont(ctypes.Structure):
        _fields_ = [('length', wintypes.ULONG), ('index', wintypes.DWORD),
                    ('size', Coord), ('family', wintypes.UINT), ('weight', wintypes.UINT),
                    ('face', wintypes.WCHAR * 32)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.restype = wintypes.HANDLE
    handle = wintypes.HANDLE(kernel.CreateFileW('CONOUT$', 0xc0000000, 3, None, 3, 0, None))
    try:
        info = ConsoleFont()
        info.length = ctypes.sizeof(info)
        if not kernel.GetCurrentConsoleFontEx(handle, False, ctypes.byref(info)):
            return ''
        info.face = face
        info.family = 54  # FF_MODERN | TMPF_TRUETYPE | TMPF_VECTOR
        if not kernel.SetCurrentConsoleFontEx(handle, False, ctypes.byref(info)):
            return ''
        if kernel.GetCurrentConsoleFontEx(handle, False, ctypes.byref(info)):
            return info.face
        return ''
    finally:
        kernel.CloseHandle(handle)


def available_face(face):
    if len(face.encode('utf-16-le')) >= 64:
        return ''
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    try:
        result = subprocess.run([sys.executable, '-I', '-B', __file__, face],
                                creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startup,
                                capture_output=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return ''
    return result.stdout.decode('utf-8') if result.returncode == 0 else ''


def configure(plan, identity, version, font):
    import console_font_registry as registry
    from fonts.model import token, windows_family

    if os.name != 'nt' or plan.library.platform != 'windows':
        raise ValueError('classic Console requires native Windows')
    target = 'classic-console'
    family = windows_family(plan.file(identity, version, font))
    actual = available_face(family)
    item = dict(id=identity, version=version, target=target, face=font['file'])
    if actual.casefold() != family.casefold():
        reason = ('Console substituted ' + actual) if actual else 'Console could not select this face'
        plan.items.append(dict(item, action='skip', reason=reason))
        return
    prior = plan.library.document['targets'].get(target, {})
    try:
        names = registry.profiles()
    except FileNotFoundError:
        plan.items.append(dict(item, action='skip', reason='No current-user Console settings'))
        return
    missing = set(prior.get('profiles', [])) - set(names)
    if missing:
        raise ValueError('classic Console font overrides changed since Set: ' + ', '.join(sorted(missing)))
    receipts = plan.library.state / 'fonts/console'
    for name in names:
        before = registry.read(name)
        if name in prior.get('profiles', []) and before != prior.get('windows_family', prior['family']):
            raise ValueError('classic Console font changed since Set: ' + (name or 'defaults'))
        if before != family:
            spec = dict(name=name, before=before, after=family)
            registry.verify(spec)
            receipt = receipts / (token(name) + '.json')
            plan.put(receipt, data=dict(schema=1, profile=name, face=family), console_face=spec)
    snapshot = json.dumps(dict.fromkeys(names, family), sort_keys=True).encode('utf-8')
    plan.document['targets'][target] = dict(item, family=font['family'], windows_family=family, path=str(receipts),
        after=hashlib.sha256(snapshot).hexdigest(), profiles=names, config=None, app_profile=None)
    plan.items.append(dict(item, action='set', profiles=names))


if __name__ == '__main__':
    # This entry point runs only in a dedicated hidden console.
    sys.stdout.buffer.write(probe(sys.argv[1]).encode('utf-8'))
