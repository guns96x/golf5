import time
import ctypes
from PIL import ImageGrab

user32 = ctypes.windll.user32

def enum_cb(hwnd, lparam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        if "MPPS" in title or "Mpps" in title:
            user32.ShowWindow(hwnd, 9)
            user32.ShowWindow(hwnd, 3)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

time.sleep(1)
im = ImageGrab.grab()
im.save(r"C:\Users\pavlo\golf5\mpps_screen_clean.png")
