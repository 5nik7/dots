"""Bounded native cache inventory and exact, exclusively pinned deletion."""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import os
import stat
import json
import subprocess
import sys

from files.file_platform import validate_windows_path
from .core import Target, fingerprint, inside
from .termux import ORDINARY, CHECKPOINTS, LOGS


class NativeReader:
    """Pin ancestors against writes/replacement and verify owner from handles."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes as w
        self.c = ctypes
        self.handles = {}
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.a = ctypes.WinDLL('advapi32', use_last_error=True)
        self.k.CreateFileW.argtypes = (w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE)
        self.k.CreateFileW.restype = w.HANDLE
        self.k.CloseHandle.argtypes = (w.HANDLE,)
        self.k.GetCurrentProcess.restype = w.HANDLE
        self.k.LocalFree.argtypes = (w.HLOCAL,)
        self.k.GetFileInformationByHandleEx.argtypes = (w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD)
        self.k.GetFileInformationByHandle.argtypes = (w.HANDLE,w.LPVOID)
        self.k.SetFileInformationByHandle.argtypes = (w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD)
        self.k.GetDriveTypeW.argtypes = (w.LPCWSTR,)
        self.k.GetVolumeInformationByHandleW.argtypes = (w.HANDLE,w.LPWSTR,w.DWORD,
            w.LPVOID,w.LPVOID,w.LPVOID,w.LPWSTR,w.DWORD)
        self.a.OpenProcessToken.argtypes = (w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE))
        self.a.GetTokenInformation.argtypes = (w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD,ctypes.POINTER(w.DWORD))
        self.a.GetSecurityInfo.argtypes = (w.HANDLE,ctypes.c_int,w.DWORD,
            ctypes.POINTER(w.LPVOID),w.LPVOID,w.LPVOID,w.LPVOID,ctypes.POINTER(w.LPVOID))
        self.a.EqualSid.argtypes = (w.LPVOID,w.LPVOID)
        self.a.ConvertSidToStringSidW.argtypes = (w.LPVOID,ctypes.POINTER(w.LPWSTR))
        self.a.GetAclInformation.argtypes = (w.LPVOID,w.LPVOID,w.DWORD,ctypes.c_int)
        self.a.GetAce.argtypes = (w.LPVOID,w.DWORD,ctypes.POINTER(w.LPVOID))
        self.token = w.HANDLE()
        if not self.a.OpenProcessToken(self.k.GetCurrentProcess(),8,ctypes.byref(self.token)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            size = w.DWORD()
            self.a.GetTokenInformation(self.token,1,None,0,ctypes.byref(size))
            self.user = ctypes.create_string_buffer(size.value)
            if not self.a.GetTokenInformation(self.token,1,self.user,size,ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            self.sid = ctypes.cast(self.user,ctypes.POINTER(w.LPVOID))[0]
        finally:
            self.k.CloseHandle(self.token)

    @contextmanager
    def opened(self, path, *, owner=False, exclusive=False, private=False, check_acl=False):
        from ctypes import wintypes as w
        c = self.c
        # READ_CONTROL + FILE_READ_ATTRIBUTES + FILE_READ_DATA/LIST_DIRECTORY;
        # share read only. Reparse objects
        # are opened themselves and refused, never followed by this scanner.
        handle = self.k.CreateFileW(str(path),0x20081 | (0x10000 if exclusive else 0),
                                   0 if exclusive else 1,None,3,0x02200000,None)
        if handle == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        alive = [True]
        self.handles[handle] = alive
        try:
            info = self.info(handle)
            if getattr(info,'st_file_attributes',0) & 0x400:
                raise ValueError('reparse point in cleanup path: ' + str(path))
            if owner:
                self.security(handle,private=private,check_acl=check_acl or exclusive or private)
            yield info, handle
        finally:
            if alive[0]:
                self.close(handle)

    def close(self, handle):
        alive = self.handles.pop(handle)
        alive[0] = False
        if not self.k.CloseHandle(handle):
            raise self.c.WinError(self.c.get_last_error())

    def sid_text(self, sid):
        from ctypes import wintypes as w
        text = w.LPWSTR()
        if not self.a.ConvertSidToStringSidW(sid,self.c.byref(text)):
            raise self.c.WinError(self.c.get_last_error())
        try:
            return text.value
        finally:
            self.k.LocalFree(text)

    def security(self, handle, *, private=False, check_acl=True):
        """Require our owner and reject untrusted allow ACEs; never rewrite ACLs."""
        from ctypes import wintypes as w
        c = self.c
        sid, acl, descriptor = w.LPVOID(), w.LPVOID(), w.LPVOID()
        error = self.a.GetSecurityInfo(handle,1,5,c.byref(sid),None,c.byref(acl),None,c.byref(descriptor))
        if error:
            raise c.WinError(error)
        try:
            if not self.a.EqualSid(sid,self.sid):
                raise ValueError('cleanup path has another owner')
            if not check_acl:
                return
            if not acl:
                raise ValueError('cleanup path has an unrestricted ACL')
            class AclSize(c.Structure):
                _fields_ = [('count',w.DWORD),('used',w.DWORD),('free',w.DWORD)]
            size = AclSize()
            if not self.a.GetAclInformation(acl,c.byref(size),c.sizeof(size),2):
                raise c.WinError(c.get_last_error())
            trusted = {self.sid_text(self.sid),'S-1-5-18'}
            if not private:
                trusted.add('S-1-5-32-544')  # Local Administrators, never arbitrary groups.
            for index in range(size.count):
                ace = w.LPVOID()
                if not self.a.GetAce(acl,index,c.byref(ace)):
                    raise c.WinError(c.get_last_error())
                header = c.string_at(ace,4)
                if header[1] & 8 or header[0] == 1:  # inherit-only or deny ACE
                    continue
                if header[0] != 0 or int.from_bytes(header[2:4],'little') < 12:
                    raise ValueError('cleanup path has an unsupported ACL entry')
                mask = c.c_uint32.from_address(ace.value+4).value
                # Writes, delete, permissions and ownership changes, including generic rights.
                unsafe = mask if private else mask & 0x500D0156
                if unsafe and self.sid_text(ace.value+8) not in trusted:
                    raise ValueError('cleanup path grants another principal ' + ('access' if private else 'write access'))
        finally:
            self.k.LocalFree(descriptor)

    def info(self, handle):
        from ctypes import wintypes as w
        from types import SimpleNamespace
        c = self.c
        class Information(c.Structure):
            _fields_ = [('attributes',w.DWORD),('created',w.FILETIME),('accessed',w.FILETIME),
                        ('written',w.FILETIME),('volume',w.DWORD),('size_hi',w.DWORD),
                        ('size_lo',w.DWORD),('links',w.DWORD),('id_hi',w.DWORD),('id_lo',w.DWORD)]
        class Basic(c.Structure):
            _fields_ = [('created',c.c_longlong),('accessed',c.c_longlong),('written',c.c_longlong),
                        ('changed',c.c_longlong),('attributes',w.DWORD)]
        info, basic = Information(), Basic()
        if not self.k.GetFileInformationByHandle(handle,c.byref(info)) or not self.k.GetFileInformationByHandleEx(handle,0,c.byref(basic),c.sizeof(basic)):
            raise c.WinError(c.get_last_error())
        directory = bool(info.attributes & 16)
        mode = (stat.S_IFDIR | 0o777) if directory else (stat.S_IFREG | (0o444 if info.attributes & 1 else 0o666))
        return SimpleNamespace(st_dev=info.volume,st_ino=(info.id_hi<<32)|info.id_lo,st_mode=mode,
            st_uid=0,st_nlink=info.links,st_size=(info.size_hi<<32)|info.size_lo,
            st_mtime_ns=(basic.written-116444736000000000)*100,
            st_ctime_ns=(basic.changed-116444736000000000)*100,st_file_attributes=info.attributes)

    def supported_volume(self, path, handle):
        from ctypes import wintypes as w
        name = self.c.create_unicode_buffer(32)
        if (self.k.GetDriveTypeW(path.anchor) != 3 or not self.k.GetVolumeInformationByHandleW(
                handle,None,0,None,None,None,name,len(name)) or name.value != 'NTFS'):
            raise ValueError('cleanup deletion requires a local NTFS volume')

    def dispose(self, handle):
        # Ordinary disposition preserves Windows mapped-file/read-only refusal.
        # No POSIX delete semantics, permission change or recursive fallback.
        value = self.c.c_ubyte(1)
        if not self.k.SetFileInformationByHandle(handle,4,self.c.byref(value),self.c.sizeof(value)):
            raise self.c.WinError(self.c.get_last_error())

    @contextmanager
    def private_attributes(self):
        from ctypes import wintypes as w
        c = self.c
        class Attributes(c.Structure):
            _fields_ = [('length',w.DWORD),('descriptor',w.LPVOID),('inherit',w.BOOL)]
        self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
            w.LPCWSTR,w.DWORD,c.POINTER(w.LPVOID),w.LPVOID)
        descriptor = w.LPVOID()
        sid = self.sid_text(self.sid)
        # Explicit protected DACL: only this user and SYSTEM. Never repair an
        # existing directory's ACL or broaden a pre-existing owner's policy.
        sddl = 'O:'+sid+'D:P(A;OICI;FA;;;'+sid+')(A;OICI;FA;;;SY)'
        if not self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,c.byref(descriptor),None):
            raise c.WinError(c.get_last_error())
        try:
            yield c.byref(Attributes(c.sizeof(Attributes),descriptor,False))
        finally:
            self.k.LocalFree(descriptor)

    def mkdir_private(self, path):
        from ctypes import wintypes as w
        self.k.CreateDirectoryW.argtypes = (w.LPCWSTR,w.LPVOID)
        with self.private_attributes() as attributes:
            if not self.k.CreateDirectoryW(str(path),attributes):
                raise self.c.WinError(self.c.get_last_error())

    def allocation(self, handle):
        from ctypes import wintypes as w
        if self.info(handle).st_file_attributes & (0x200 | 0x800):
            class CompressionInfo(self.c.Structure):
                _fields_ = [('allocated',self.c.c_longlong),('format',w.WORD),
                            ('unit',self.c.c_ubyte),('chunk',self.c.c_ubyte),
                            ('cluster',self.c.c_ubyte),('reserved',self.c.c_ubyte*3)]
            info = CompressionInfo()
            if not self.k.GetFileInformationByHandleEx(handle,8,self.c.byref(info),self.c.sizeof(info)):
                raise self.c.WinError(self.c.get_last_error())
            if info.allocated < 0:
                raise ValueError('invalid native sparse/compressed allocation')
            return info.allocated
        class StandardInfo(self.c.Structure):
            _fields_ = [('allocation',self.c.c_longlong),('size',self.c.c_longlong),
                        ('links',w.DWORD),('delete_pending',self.c.c_ubyte),('directory',self.c.c_ubyte)]
        info = StandardInfo()
        if not self.k.GetFileInformationByHandleEx(handle,1,self.c.byref(info),self.c.sizeof(info)):
            raise self.c.WinError(self.c.get_last_error())
        if info.allocation < 0:
            raise ValueError('invalid native file allocation')
        return info.allocation

    def children(self, handle):
        """Enumerate the pinned directory without a second path-based open."""
        from ctypes import wintypes as w
        c = self.c
        class Entry(c.Structure):
            _fields_ = [('next',w.DWORD),('index',w.DWORD),('created',c.c_longlong),
                ('accessed',c.c_longlong),('written',c.c_longlong),('changed',c.c_longlong),
                ('size',c.c_longlong),('allocated',c.c_longlong),('attributes',w.DWORD),
                ('length',w.DWORD),('ea',w.DWORD),('short_length',c.c_byte),
                ('short',w.WCHAR*12),('identity',c.c_longlong),('name',w.WCHAR*1)]
        result = set()
        buffer = c.create_string_buffer(65536)
        restart = True
        while True:
            if not self.k.GetFileInformationByHandleEx(handle,11 if restart else 10,buffer,len(buffer)):
                error = c.get_last_error()
                if error == 18:
                    return result
                raise c.WinError(error)
            restart = False
            offset = 0
            while True:
                if offset+Entry.name.offset > len(buffer):
                    raise ValueError('invalid native directory enumeration')
                entry = c.cast(c.addressof(buffer)+offset,c.POINTER(Entry)).contents
                if entry.length % 2 or offset+Entry.name.offset+entry.length > len(buffer):
                    raise ValueError('invalid native directory entry')
                name = c.string_at(c.addressof(buffer)+offset+Entry.name.offset,entry.length).decode('utf-16-le')
                if name not in ('.','..'):
                    if name in result:
                        raise ValueError('native directory enumeration changed')
                    result.add(name)
                if not entry.next:
                    break
                if entry.next < Entry.name.offset+entry.length:
                    raise ValueError('invalid native directory offset')
                offset += entry.next


class PinnedGroup:
    """Hold the reviewed group exclusively; no delete occurs while preparing."""
    def __init__(self, targets, boundary):
        self.reader = NativeReader()
        self.stack = ExitStack()
        self.objects = {}
        self.targets = targets
        self.boundary = boundary

    def __enter__(self):
        try:
            # Bound handle/resource usage. Larger inventories remain untouched.
            if sum(len(target.entries) for target in self.targets) > 50000:
                raise ValueError('native cleanup group exceeds the 50000-entry safety bound')
            for target in self.targets:
                validate_windows_path(target.path)
                if not inside(target.path,self.boundary) or target.path == self.boundary:
                    raise ValueError('cleanup target escapes its native home boundary')
                for parent in reversed(target.path.parents):
                    if parent not in self.objects:
                        self.objects[parent] = self.stack.enter_context(self.reader.opened(parent,
                            owner=inside(parent,self.boundary),check_acl=inside(parent,self.boundary)))
                for name in sorted(target.entries,key=lambda name: len(Path(name).parts)):
                    path = target.path if name == '.' else target.path/name
                    validate_windows_path(path)
                    if path in self.objects:
                        raise ValueError('overlapping native cleanup targets')
                    info, handle = self.stack.enter_context(self.reader.opened(path,owner=True,exclusive=True))
                    self.objects[path] = (info,handle)
                    self.reader.supported_volume(path,handle)
                    if info.st_dev != self.objects[self.boundary][0].st_dev:
                        raise ValueError('foreign cleanup volume')
                    if info.st_file_attributes & (1 | 4 | 0x1000) or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
                        raise ValueError('read-only, system, offline or multiply-linked cleanup entry')
                if self.inventory(target,self.boundary) != target.entries:
                    raise ValueError('native cleanup group changed since review')
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def inventory(self, target, boundary):
        entries = {}
        for name in target.entries:
            path = target.path if name == '.' else target.path/name
            if path not in self.objects:
                try:
                    path.lstat()
                except FileNotFoundError:
                    continue
                else:
                    raise ValueError('entry reappeared during native cleanup')
            info, handle = self.objects[path]
            current = self.reader.info(handle)
            record = fingerprint(current)
            entries[name] = (*record[:8],self.reader.allocation(handle) if stat.S_ISREG(current.st_mode) else 0)
            if stat.S_ISDIR(current.st_mode):
                expected = {p.name for p in self.objects if p.parent == path}
                if self.reader.children(handle) != expected:
                    raise ValueError('directory entries changed during native cleanup')
        return entries

    def delete_entries(self, target, boundary, progress=lambda *args: None, confirmed=None):
        if self.inventory(target,boundary) != target.entries:
            raise ValueError('native cleanup target changed before deletion')
        names = sorted(target.entries,key=lambda name: len(Path(name).parts),reverse=True)
        for count, name in enumerate(names,1):
            if name == '.' and target.mode == 'contents':
                continue
            path = target.path if name == '.' else target.path/name
            info, handle = self.objects[path]
            current = fingerprint(self.reader.info(handle))
            expected = target.entries[name]
            if current[:4] != expected[:4] or (not stat.S_ISDIR(info.st_mode) and current[4:8] != expected[4:8]):
                raise ValueError('native cleanup entry changed before deletion')
            self.reader.security(handle)
            self.reader.dispose(handle)
            # A metadata-only handle can outlive a delete request, and a racing
            # hardlink must never inflate reclaimed-space accounting.
            links = self.reader.info(handle).st_nlink
            # The exclusive handle was the final I/O handle. Close immediately,
            # then credit only an absent exact name; uncertain outcomes get zero.
            self.reader.close(handle)
            del self.objects[path]
            try:
                path.lstat()
            except FileNotFoundError:
                pass
            else:
                raise ValueError('native cleanup removal could not be confirmed')
            if confirmed is not None:
                confirmed[name] = (*expected[:4],links,*expected[5:])
            progress('Removing '+target.rule,count,len(names))


def reference_probe(paths, owner_pid):
    """Query Restart Manager only; no shutdown/restart API is loaded or called."""
    import ctypes as c
    from ctypes import wintypes as w
    class Process(c.Structure):
        _fields_ = [('pid',w.DWORD),('started',w.FILETIME)]
    class Information(c.Structure):
        _fields_ = [('process',Process),('application',w.WCHAR*256),('service',w.WCHAR*64),
                    ('kind',c.c_int),('status',w.ULONG),('session',w.DWORD),('restartable',w.BOOL)]
    rm = c.WinDLL('rstrtmgr',use_last_error=True)
    rm.RmStartSession.argtypes = (c.POINTER(w.DWORD),w.DWORD,w.LPWSTR)
    rm.RmRegisterResources.argtypes = (w.DWORD,w.UINT,c.POINTER(w.LPCWSTR),w.UINT,w.LPVOID,w.UINT,w.LPVOID)
    rm.RmGetList.argtypes = (w.DWORD,c.POINTER(w.UINT),c.POINTER(w.UINT),w.LPVOID,c.POINTER(w.DWORD))
    rm.RmEndSession.argtypes = (w.DWORD,)
    session = w.DWORD()
    key = c.create_unicode_buffer(33)
    error = rm.RmStartSession(c.byref(session),0,key)
    if error:
        raise c.WinError(error)
    try:
        # Registration changes Restart Manager's transient session metadata.
        # This function is reachable only from an explicitly approved run.
        for offset in range(0,len(paths),256):
            batch = paths[offset:offset+256]
            error = rm.RmRegisterResources(session,len(batch),(w.LPCWSTR*len(batch))(*batch),0,None,0,None)
            if error:
                raise c.WinError(error)
        needed, count, reboot = w.UINT(), w.UINT(), w.DWORD()
        error = rm.RmGetList(session,c.byref(needed),c.byref(count),None,c.byref(reboot))
        if error not in (0,234) or (error == 234 and not needed.value) or reboot.value or needed.value > 4096:
            raise ValueError('native process-reference inspection is incomplete')
        if not needed.value:
            return False
        count.value = needed.value
        rows = (Information*count.value)()
        error = rm.RmGetList(session,c.byref(needed),c.byref(count),rows,c.byref(reboot))
        if error or reboot.value:
            raise ValueError('native process-reference inspection changed or failed')
        # Only the still-running parent owns the cleanup group's exclusive pins.
        return any(row.process.pid != owner_pid for row in rows[:count.value])
    finally:
        error = rm.RmEndSession(session)
        if error:
            raise c.WinError(error)


def process_references(paths, owner_pid):
    if not paths:
        return [], []
    code = ('import json,sys;sys.path.insert(0,sys.argv[1]);'
            'from cleanup.windows import reference_probe;'
            'print(json.dumps(reference_probe(json.load(sys.stdin),int(sys.argv[2]))))')
    try:
        result = subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parents[1]),str(owner_pid)],
            input=json.dumps(paths),text=True,capture_output=True,timeout=20)
        if result.returncode or result.stderr or result.stdout.strip() not in ('true','false'):
            return [], ['native process-reference inspection failed']
        return (paths if result.stdout.strip() == 'true' else []), []
    except (OSError,subprocess.TimeoutExpired):
        return [], ['native process-reference inspection unavailable or timed out']

def inventory(target, boundary):
    path = target.path
    validate_windows_path(path)
    if not inside(path,boundary) or path == boundary or '..' in path.parts:
        raise ValueError('cleanup target escapes its native home boundary')
    reader = NativeReader()
    entries = {}
    with ExitStack() as ancestors:
        for parent in reversed(path.parents):
            if not os.path.lexists(parent):
                return {}
            ancestors.enter_context(reader.opened(parent,owner=inside(parent,boundary)))
        if not os.path.lexists(path):
            return {}
        with reader.opened(boundary,owner=True) as (boundary_info, _):
            device = boundary_info.st_dev
        def visit(item):
            with reader.opened(item,owner=True) as (info,handle):
                if info.st_dev != device or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                    raise ValueError('foreign filesystem or special cleanup file: ' + str(item))
                record = fingerprint(info)
                allocation = reader.allocation(handle) if stat.S_ISREG(info.st_mode) else 0
                entries[str(item.relative_to(path))] = (*record[:8],allocation)
                if stat.S_ISDIR(info.st_mode):
                    for child in sorted(item.iterdir()):
                        visit(child)
                if fingerprint(reader.info(handle)) != record:
                    raise ValueError('cleanup entry changed during scan: ' + str(item))
        visit(path)
    if target.mode == 'file' and not stat.S_ISREG(entries['.'][2]):
        raise ValueError('expected a regular cleanup log')
    if target.mode != 'file' and not stat.S_ISDIR(entries['.'][2]):
        raise ValueError('expected a cleanup cache directory')
    return entries


class Windows:
    platform = 'windows'
    supported_groups = ('downloads', 'logs')
    can_delete = True

    def __init__(self, env=None):
        if os.name != 'nt':
            raise ValueError('Windows cleanup requires a native Windows runtime')
        self.env = dict(os.environ if env is None else env)
        self.home = Path(self.env.get('HOME') or self.env.get('USERPROFILE') or '')
        validate_windows_path(self.home)
        if self.home == Path(self.home.anchor) or not self.home.is_dir():
            raise ValueError('cleanup requires an existing native home')
        self.boundary = self.home
        self.pinned = None
        self.local = Path(self.env.get('LOCALAPPDATA') or self.home/'AppData/Local')
        validate_windows_path(self.local)
        if not inside(self.local,self.home) or self.local == self.home:
            raise ValueError('cleanup requires home-bounded LocalAppData')

    def candidates(self, groups, age_days, report=lambda *args: None):
        targets, issues = [], []
        def add(rule, group, path, mode='contents'):
            target = Target(rule,group,path,mode,reason='Known disposable native cache or diagnostic log')
            try:
                target.entries = inventory(target,self.boundary)
                if any(name != '.' or mode != 'contents' for name in target.entries):
                    targets.append(target)
            except (OSError,ValueError) as error:
                issues.append(dict(group=group,rule=rule,path=str(path),reason=str(error)))
            report('Scanning ' + rule)
        if 'downloads' in groups:
            # Defaults documented by npm and pip; custom locations are retained.
            for rule, variable, path in (
                ('npm-cache','npm_config_cache',self.local/'npm-cache/_cacache'),
                ('pip-cache','PIP_CACHE_DIR',self.local/'pip/Cache')):
                if self.env.get(variable):
                    issues.append(dict(group='downloads',rule=rule,reason='Custom cache location requires native review: ' + variable))
                else:
                    add(rule,'downloads',path)
        if 'builds' in groups:
            issues.append(dict(group='builds',reason='Native build-cache ownership and helper acceptance remain pending'))
        if 'logs' in groups:
            for name in LOGS:
                add('nvim-logs','logs',self.local/'nvim-data'/name,'file')
        for group in groups:
            if group in CHECKPOINTS:
                issues.append(dict(group=group,reason='Native checkpoint cleanup is not implemented'))
        return targets, issues

    @contextmanager
    def guard(self, members, inspect=None):
        if sum(len(target.entries) for target in members) > 50000:
            raise ValueError('native cleanup group exceeds the 50000-entry safety bound')
        # Before our own pins exist, include this process too (for example an
        # interpreter or mapped file inside a cache). A second query under the
        # pins may exempt only the still-running pin-owning process.
        files = [str(target.path if name == '.' else target.path/name)
                 for target in members for name,info in target.entries.items() if stat.S_ISREG(info[2])]
        active, unknown = inspect([target.path for target in members]) if inspect else process_references(files,0)
        if active or unknown:
            raise ValueError('active or uninspectable processes; native group retained')
        with PinnedGroup(members,self.boundary) as pinned:
            self.pinned = pinned
            try:
                yield
            finally:
                self.pinned = None

    def inventory(self, target, boundary):
        return self.pinned.inventory(target,boundary) if self.pinned else inventory(target,boundary)

    def references(self, paths):
        if self.pinned is None:
            return [], ['native cleanup group has not been pinned']
        files = [str(path) for path,(info,_) in self.pinned.objects.items()
                 if stat.S_ISREG(info.st_mode) and any(inside(path,root) for root in paths)]
        return process_references(files,os.getpid())

    def delete_entries(self, target, boundary, progress, confirmed):
        if self.pinned is None:
            raise ValueError('native cleanup group has not been pinned')
        return self.pinned.delete_entries(target,boundary,progress,confirmed)
