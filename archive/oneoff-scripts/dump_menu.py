import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

output = []

def dump_menu(hmenu, indent=""):
    count = user32.GetMenuItemCount(hmenu)
    for i in range(count):
        buff = ctypes.create_unicode_buffer(256)
        user32.GetMenuStringW(hmenu, i, buff, 256, 0x0400)
        submenu = user32.GetSubMenu(hmenu, i)
        cmd_id = user32.GetMenuItemID(hmenu, i)
        output.append(f"{indent}[{i}] {buff.value} (ID: {cmd_id})")
        if submenu:
            dump_menu(submenu, indent + "  ")

def enum_cb(hwnd, lparam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        if "MPPS" in title or "Mpps" in title:
            hmenu = user32.GetMenu(hwnd)
            if hmenu:
                output.append(f"Menu for hwnd={hwnd} ({title}):")
                dump_menu(hmenu)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

with open(r"C:\Users\pavlo\golf5\mpps_menu.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
