"""Create the shared Windows font state with an inheritable administrator DACL."""
import ctypes as c
from ctypes import wintypes as w


# OWNER RIGHTS limits implicit owner privileges when a child was created by an
# elevated user whose default owner SID is their individual account.
DESCRIPTOR = 'O:BAD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;OICI;0x1200a9;;;BU)(A;OICI;RC;;;OW)'


def check_directory(path, *, create=False):
    """Verify an existing root, or atomically create it with its final permissions."""
    if not create and not path.exists():
        return
    kernel = c.WinDLL('kernel32', use_last_error=True)
    security = c.WinDLL('advapi32', use_last_error=True)
    kernel.LocalFree.argtypes = (w.HLOCAL,)
    kernel.CreateDirectoryW.argtypes = (w.LPCWSTR, w.LPVOID)
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
        w.LPCWSTR, w.DWORD, c.POINTER(w.LPVOID), w.LPVOID)
    security.GetNamedSecurityInfoW.argtypes = (
        w.LPCWSTR, c.c_int, w.DWORD, w.LPVOID, w.LPVOID, w.LPVOID, w.LPVOID, c.POINTER(w.LPVOID))
    security.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = (
        w.LPVOID, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), w.LPVOID)
    class Attributes(c.Structure):
        _fields_ = [('size', w.DWORD), ('descriptor', w.LPVOID), ('inherit', w.BOOL)]

    owner_and_dacl = 5
    def canonical(descriptor):
        value = w.LPWSTR()
        if not security.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, 1, owner_and_dacl, c.byref(value), None):
            raise c.WinError(c.get_last_error())
        try:
            return value.value.replace('D:PAI(', 'D:P(')
        finally:
            kernel.LocalFree(value)

    expected = w.LPVOID()
    actual = w.LPVOID()
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(DESCRIPTOR, 1, c.byref(expected), None):
        raise c.WinError(c.get_last_error())
    try:
        if create:
            attributes = Attributes(c.sizeof(Attributes), expected, False)
            if not kernel.CreateDirectoryW(str(path), c.byref(attributes)) and c.get_last_error() != 183:
                raise c.WinError(c.get_last_error())
        error = security.GetNamedSecurityInfoW(str(path), 1, owner_and_dacl, None, None, None, None, c.byref(actual))
        if error:
            raise c.WinError(error)
        if canonical(actual) != canonical(expected):
            raise ValueError('machine font state requires its administrator-owned permissions: ' + str(path))
    finally:
        if actual: kernel.LocalFree(actual)
        kernel.LocalFree(expected)
