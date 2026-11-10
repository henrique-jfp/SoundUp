import winreg

key = winreg.OpenKey(
    winreg.HKEY_LOCAL_MACHINE,
    r"SYSTEM\CurrentControlSet\Control\Session Manager",
)
try:
    value, kind = winreg.QueryValueEx(key, "PendingFileRenameOperations")
except FileNotFoundError:
    print("sem operacoes pendentes")
else:
    print("entradas:", len(value))
    for index in range(0, len(value), 2):
        source = value[index]
        target = value[index + 1] if index + 1 < len(value) else "(sem par)"
        print(f"{index // 2}: {source!r} -> {target!r}")
