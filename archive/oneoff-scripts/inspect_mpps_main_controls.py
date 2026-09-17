import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

output = []

def enum_child_cb(hwnd, lparam):
    text_len = user32.GetWindowTextLengthW(hwnd)
    text_buff = ctypes.create_unicode_buffer(text_len + 1)
    user32.GetWindowTextW(hwnd, text_buff, text_len + 1)
    
    cls_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls_buff, 256)
    
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    vis = user32.IsWindowVisible(hwnd)
    enabled = user32.IsWindowEnabled(hwnd)
    
    output.append(f"hwnd={hwnd} class='{cls_buff.value}' text='{text_buff.value}' vis={vis} en={enabled} rect=[{r.left},{r.top},{r.right},{r.bottom}]")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumChildWindows(3016528, WNDENUMPROC(enum_child_cb), 0)

with open(r"C:\Users\pavlo\golf5\main_controls.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
