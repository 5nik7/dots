"""Private native storage for the existing cleanup receipt schema."""
from contextlib import ExitStack, contextmanager
from pathlib import Path
import json
import os
import stat
import uuid

from files.file_platform import validate_windows_path
from .windows import NativeReader


class Storage:
    def __init__(self, directory):
        self.directory = directory
        self.reader = NativeReader()
        self.stack = None
        self.lock = None
        self.report_handle = None
        self.report_id = None
        self.failed = False

    @contextmanager
    def pinned(self, create=False):
        validate_windows_path(self.directory)
        with ExitStack() as stack:
            for path in [*reversed(self.directory.parents),self.directory]:
                if not os.path.lexists(path):
                    if not create:
                        yield False
                        return
                    self.reader.mkdir_private(path)
                info, handle = stack.enter_context(self.reader.opened(path,
                    owner=path == self.directory,private=path == self.directory))
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError('cleanup receipt ancestor is not a directory')
                if path == self.directory:
                    self.reader.supported_volume(path,handle)
            yield True

    def check(self):
        with self.pinned():
            pass

    def acquire(self):
        from ctypes import wintypes as w
        self.stack = ExitStack()
        self.failed = False
        try:
            self.stack.enter_context(self.pinned(create=True))
            with self.reader.private_attributes() as attributes:
                handle = self.reader.k.CreateFileW(str(self.directory/'lock'),0xC0020080,
                    0,attributes,4,0x00200000,None)
            if handle == self.reader.c.c_void_p(-1).value:
                raise ValueError('cleanup receipt lock is unavailable or another run is active')
            self.lock = handle
            info = self.reader.info(handle)
            if info.st_file_attributes & 0x400 or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('invalid native cleanup receipt lock')
            self.reader.security(handle,private=True)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.report_handle is not None:
            self.reader.k.CloseHandle(self.report_handle)
            self.report_handle = None
            self.report_id = None
        if self.lock is not None:
            self.reader.k.CloseHandle(self.lock)
            self.lock = None
        if self.stack is not None:
            self.stack.close()
            self.stack = None

    def read(self, path):
        from ctypes import wintypes as w
        c, k = self.reader.c, self.reader.k
        k.ReadFile.argtypes = (w.HANDLE,w.LPVOID,w.DWORD,c.POINTER(w.DWORD),w.LPVOID)
        with self.pinned() as present:
            if not present:
                raise ValueError('cleanup receipt directory disappeared')
            with self.reader.opened(path,owner=True,private=True) as (info,handle):
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 16*1024*1024:
                    raise ValueError('invalid native cleanup receipt')
                data = c.create_string_buffer(info.st_size+1)
                read = w.DWORD()
                if not k.ReadFile(handle,data,info.st_size+1,c.byref(read),None):
                    raise c.WinError(c.get_last_error())
                if read.value != info.st_size:
                    raise ValueError('native cleanup receipt changed during read')
                payload = data.raw[:read.value]
                if path.suffix == '.json':
                    return json.loads(payload)
                last = None
                interrupted = False
                for line in payload.splitlines(keepends=True):
                    if not line.endswith(b'\n'):
                        interrupted = True
                        break
                    row = json.loads(line)
                    if not isinstance(row,dict) or row.get('id') != path.stem or row.get('schema') != 1:
                        raise ValueError('invalid native cleanup receipt snapshot')
                    last = row
                if last is None:
                    raise ValueError('native cleanup receipt has no complete snapshot')
                return dict(last,status='running') if interrupted else last

    def paths(self):
        with self.pinned() as present:
            if not present:
                return []
            paths = [path for path in self.directory.iterdir() if path.suffix in ('.json','.jsonl')]
            if len({path.stem for path in paths}) != len(paths):
                raise ValueError('duplicate cleanup receipt identity')
            return paths

    def write(self, report):
        from ctypes import wintypes as w
        if self.lock is None:
            raise ValueError('native cleanup receipt write requires its exclusive lock')
        if self.failed:
            raise ValueError('native cleanup receipt write previously failed; refusing another append')
        c, k = self.reader.c, self.reader.k
        self.check()
        identity = str(uuid.UUID(report['id']))
        if self.report_id is not None and identity != self.report_id:
            raise ValueError('native cleanup receipt identity changed during the run')
        if self.report_handle is None:
            if os.path.lexists(self.directory/(identity+'.json')):
                raise ValueError('native cleanup receipt identity already exists')
            with self.reader.private_attributes() as attributes:
                handle = k.CreateFileW(str(self.directory/(identity+'.jsonl')),0xC0020080,
                    0,attributes,1,0x00200000,None)
            if handle == c.c_void_p(-1).value:
                raise c.WinError(c.get_last_error())
            self.report_handle, self.report_id = handle, identity
        handle = self.report_handle
        self.reader.security(handle,private=True)
        payload = (json.dumps(report,ensure_ascii=True)+'\n').encode('utf-8')
        if self.reader.info(handle).st_size + len(payload) > 16*1024*1024:
            raise ValueError('native cleanup receipt reached its bounded size; run retained')
        k.WriteFile.argtypes = (w.HANDLE,w.LPCVOID,w.DWORD,c.POINTER(w.DWORD),w.LPVOID)
        k.FlushFileBuffers.argtypes = (w.HANDLE,)
        written = w.DWORD()
        try:
            if not k.WriteFile(handle,payload,len(payload),c.byref(written),None) or written.value != len(payload):
                raise c.WinError(c.get_last_error())
            if not k.FlushFileBuffers(handle):
                raise c.WinError(c.get_last_error())
        except BaseException:
            self.failed = True
            raise
