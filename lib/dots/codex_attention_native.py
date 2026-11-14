"""Native Windows attention identity and private-state primitives.

No terminal titles, process command lines, conversations or notification APIs
are read. An observer's process identity is not a Codex pane/thread identity.
"""
from contextlib import contextmanager, ExitStack
import os
from pathlib import Path
import re


class Windows:
    def __init__(self):
        if os.name != 'nt':
            raise ValueError('native Windows attention requires Windows')
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.security = c.WinDLL('advapi32', use_last_error=True)
        k, a = self.kernel, self.security
        k.GetCurrentProcess.restype = w.HANDLE
        k.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
        k.OpenProcess.restype = w.HANDLE
        k.CloseHandle.argtypes = (w.HANDLE,)
        k.GetProcessTimes.argtypes = (w.HANDLE, *([c.POINTER(w.FILETIME)] * 4))
        k.WaitForSingleObject.argtypes = (w.HANDLE, w.DWORD)
        k.WaitForSingleObject.restype = w.DWORD
        k.LocalFree.argtypes = (w.HLOCAL,)
        a.OpenProcessToken.argtypes = (w.HANDLE, w.DWORD, c.POINTER(w.HANDLE))
        a.GetTokenInformation.argtypes = (w.HANDLE, c.c_int, w.LPVOID, w.DWORD, c.POINTER(w.DWORD))
        a.EqualSid.argtypes = (w.LPVOID, w.LPVOID)
        a.ConvertSidToStringSidW.argtypes = (w.LPVOID, c.POINTER(w.LPWSTR))
        k.CreateFileW.argtypes = (w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE)
        k.CreateFileW.restype = w.HANDLE
        k.CreateDirectoryW.argtypes = (w.LPCWSTR, w.LPVOID)
        k.GetFileInformationByHandleEx.argtypes = (w.HANDLE, c.c_int, w.LPVOID, w.DWORD)
        a.GetSecurityInfo.argtypes = (w.HANDLE, c.c_int, w.DWORD, c.POINTER(w.LPVOID),
                                     w.LPVOID, c.POINTER(w.LPVOID), w.LPVOID, c.POINTER(w.LPVOID))
        a.GetAce.argtypes = (w.LPVOID, w.DWORD, c.POINTER(w.LPVOID))
        a.GetSecurityDescriptorControl.argtypes = (w.LPVOID, c.POINTER(w.WORD), c.POINTER(w.DWORD))
        a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (w.LPCWSTR, w.DWORD, c.POINTER(w.LPVOID), w.LPVOID)
        self.user = self.process_user(k.GetCurrentProcess())
        self.sid = c.cast(self.user, c.POINTER(w.LPVOID))[0]

    def checked(self, result):
        if not result:
            raise self.c.WinError(self.c.get_last_error())
        return result

    def process_user(self, process):
        c, w = self.c, self.w
        token = w.HANDLE()
        self.checked(self.security.OpenProcessToken(process, 8, c.byref(token)))
        try:
            size = w.DWORD()
            self.security.GetTokenInformation(token, 1, None, 0, c.byref(size))
            if not 0 < size.value <= 65536:
                raise ValueError('invalid process token size')
            user = c.create_string_buffer(size.value)
            self.checked(self.security.GetTokenInformation(token, 1, user, size, c.byref(size)))
            return user
        finally:
            self.kernel.CloseHandle(token)

    def identity(self, pid):
        """Validate a live same-user process by PID and creation time."""
        if type(pid) is not int or not 0 < pid <= 0xffffffff:
            raise ValueError('invalid process identity')
        c, w = self.c, self.w
        process = self.checked(self.kernel.OpenProcess(0x101000, False, pid))
        try:
            user = self.process_user(process)
            if not self.security.EqualSid(self.sid, c.cast(user, c.POINTER(w.LPVOID))[0]):
                raise ValueError('foreign process identity')
            if self.kernel.WaitForSingleObject(process, 0) != 258:  # WAIT_TIMEOUT
                raise ValueError('process is not running')
            times = [w.FILETIME() for _ in range(4)]
            self.checked(self.kernel.GetProcessTimes(process, *(c.byref(value) for value in times)))
            started = times[0].dwLowDateTime | (times[0].dwHighDateTime << 32)
            if not started:
                raise ValueError('missing process creation time')
            return {'pid': pid, 'started': started}
        finally:
            self.kernel.CloseHandle(process)

    def matches(self, identity):
        try:
            return (isinstance(identity, dict) and set(identity) == {'pid', 'started'} and
                    type(identity['started']) is int and self.identity(identity['pid']) == identity)
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def sid_text(self, sid):
        value = self.w.LPWSTR()
        self.checked(self.security.ConvertSidToStringSidW(sid, self.c.byref(value)))
        try:
            return value.value
        finally:
            self.kernel.LocalFree(value)

    def mkdir(self, path):
        """Create a new private directory atomically; never change existing ACLs."""
        c, w = self.c, self.w
        class Attributes(c.Structure):
            _fields_ = [('length', w.DWORD), ('descriptor', w.LPVOID), ('inherit', w.BOOL)]
        sid = self.sid_text(self.sid)
        descriptor = w.LPVOID()
        self.checked(self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            'O:'+sid+'D:P(A;OICI;FA;;;'+sid+')(A;OICI;FA;;;SY)', 1, c.byref(descriptor), None))
        try:
            attrs = Attributes(c.sizeof(Attributes), descriptor, False)
            if not self.kernel.CreateDirectoryW(str(path), c.byref(attrs)) and c.get_last_error() != 183:
                raise c.WinError(c.get_last_error())
        finally:
            self.kernel.LocalFree(descriptor)

    def private(self, handle, *, directory=False):
        c, w = self.c, self.w
        owner, acl, descriptor = w.LPVOID(), w.LPVOID(), w.LPVOID()
        error = self.security.GetSecurityInfo(handle, 1, 5, c.byref(owner), None,
                                              c.byref(acl), None, c.byref(descriptor))
        if error:
            raise c.WinError(error)
        try:
            if not owner or not self.security.EqualSid(owner, self.sid) or not acl:
                raise ValueError('attention state must have the current owner and a private DACL')
            if directory:
                control, revision = w.WORD(), w.DWORD()
                self.checked(self.security.GetSecurityDescriptorControl(descriptor, c.byref(control), c.byref(revision)))
                if not control.value & 0x1000:  # SE_DACL_PROTECTED
                    raise ValueError('attention directory must have a protected DACL')
            header = c.string_at(acl, 8)
            count = int.from_bytes(header[4:6], 'little')
            if not 1 <= count <= 16:
                raise ValueError('unsupported attention DACL')
            for index in range(count):
                ace = w.LPVOID()
                self.checked(self.security.GetAce(acl, index, c.byref(ace)))
                head = c.string_at(ace, 4)
                if head[0] != 0 or int.from_bytes(head[2:4], 'little') < 12:
                    raise ValueError('unsupported attention access rule')
                sid = w.LPVOID(ace.value + 8)
                if not self.security.EqualSid(sid, self.sid) and self.sid_text(sid) != 'S-1-5-18':
                    raise ValueError('attention state grants access to another principal')
        finally:
            self.kernel.LocalFree(descriptor)

    @contextmanager
    def opened(self, path, *, private=False, directory=False, writable=False):
        c, w = self.c, self.w
        # Open the object itself and pin it against replacement. Read snapshots
        # also deny concurrent write handles, so immutable SQLite reads are safe.
        # FILE_READ_DATA/LIST_DIRECTORY is required: metadata-only access does
        # not participate in Windows sharing checks and cannot pin this path.
        handle = self.kernel.CreateFileW(str(path), 0x20081, 3 if writable else 1,
                                        None, 3, 0x02200000, None)
        if handle == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        try:
            attributes = (w.DWORD * 2)()
            self.checked(self.kernel.GetFileInformationByHandleEx(handle, 9, attributes, c.sizeof(attributes)))
            if attributes[0] & 0x400 or bool(attributes[0] & 0x10) != directory:
                raise ValueError('attention state refuses reparse points and unexpected types')
            if not directory and path.stat().st_nlink != 1:
                raise ValueError('attention state refuses hardlinks')
            if private:
                self.private(handle, directory=directory)
            yield handle
        finally:
            self.kernel.CloseHandle(handle)

    @contextmanager
    def runtime(self, root, *, create=True):
        """Pin the one existing queue namespace; all SQLite sidecars stay private."""
        from files.file_platform import validate_windows_path
        root = Path(root)
        validate_windows_path(root)
        if root == Path(root.anchor):
            raise ValueError('attention root cannot be a drive root')
        if not create and not os.path.lexists(root):
            yield None
            return
        with ExitStack() as opened:
            for path in [*reversed(root.parents), root]:
                if not os.path.lexists(path):
                    if not create:
                        yield None
                        return
                    self.mkdir(path)
                opened.enter_context(self.opened(path, directory=True, private=path == root))
            database = root/'events.sqlite3'
            # SQLite uses its own rollback journal, not a second event store.
            # Refuse unexpected WAL/SHM state for noncreating snapshot reads.
            for suffix in ('-journal', '-wal', '-shm'):
                sidecar = Path(str(database) + suffix)
                if os.path.lexists(sidecar):
                    if not create:
                        raise ValueError('attention queue is busy; retry its snapshot')
                    with self.opened(sidecar, private=True, writable=True):
                        pass
            if os.path.lexists(database):
                opened.enter_context(self.opened(database, private=True, writable=create))
            elif not create:
                yield None
                return
            yield database
            # Newly created database/sidecars inherit only current-user/SYSTEM
            # rights from the protected directory. Verify before releasing it.
            for suffix in ('', '-journal', '-wal', '-shm'):
                path = Path(str(database) + suffix)
                if os.path.lexists(path):
                    with self.opened(path, private=True, writable=create):
                        pass

    def read_private(self, path, limit):
        """Read an existing owned marker while pinning every ancestor."""
        from files.file_platform import validate_windows_path
        path = Path(path)
        validate_windows_path(path)
        with ExitStack() as opened:
            for parent in reversed(path.parents):
                opened.enter_context(self.opened(parent, directory=True))
            opened.enter_context(self.opened(path, private=True))
            with path.open('rb') as stream:
                raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('oversized attention marker')
            return raw


def context(env=None, native=None):
    """Read-only capability evidence; inherited terminal hints never imply view."""
    env = os.environ if env is None else env
    native = Windows() if native is None else native
    return {
        'schema': 1, 'platform': 'windows', 'observer': native.identity(os.getpid()),
        'terminal_hints': {
            'windows_terminal': bool(re.fullmatch(r'[0-9a-fA-F-]{36}', env.get('WT_SESSION', ''))),
            'wezterm': bool(re.fullmatch(r'[0-9]{1,12}', env.get('WEZTERM_PANE', ''))),
        },
        'pane_identity': None, 'thread_identity': None, 'focused': None,
        'automatic_acknowledgement': False, 'delivery_owner': 'existing-notifier',
        'event_source': 'owned-marker-and-observational-callback-required',
        'delivery': 'none-record-only', 'explicit_event_acknowledgement': True,
        'reason': 'Inherited terminal hints and observer identity do not prove a visible Codex pane or thread.',
    }
