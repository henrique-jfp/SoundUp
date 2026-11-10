import ctypes
from ctypes import wintypes
import winreg

advapi = ctypes.WinDLL("advapi32", use_last_error=True)


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


def key_last_write(root, path, view=winreg.KEY_WOW64_64KEY):
    key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | view)
    last_write = FILETIME()
    classes = wintypes.DWORD()
    subkeys = wintypes.DWORD()
    values = wintypes.DWORD()
    max_class = wintypes.DWORD()
    max_subkey = wintypes.DWORD()
    max_value = wintypes.DWORD()
    max_data = wintypes.DWORD()
    security = wintypes.DWORD()
    result = advapi.RegQueryInfoKeyW(
        key.handle,
        None,
        ctypes.byref(classes),
        ctypes.byref(subkeys),
        ctypes.byref(max_subkey),
        ctypes.byref(max_class),
        ctypes.byref(values),
        ctypes.byref(max_value),
        ctypes.byref(max_data),
        ctypes.byref(security),
        ctypes.byref(last_write),
    )
    if result != 0:
        raise OSError(result, "RegQueryInfoKeyW falhou")
    ticks = (last_write.dwHighDateTime << 32) | last_write.dwLowDateTime
    import datetime
    return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ticks / 10)


path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EqualizerAPO"
print("64-bit:", key_last_write(winreg.HKEY_LOCAL_MACHINE, path))
