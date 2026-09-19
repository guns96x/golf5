import time
import ctypes

user32 = ctypes.windll.user32

found_btn = [0]
def enum_cb(hwnd, lparam):
    cls_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls_buff, 256)
    txt_buff = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, txt_buff, 256)
    if cls_buff.value == "Button" and "OK" in txt_buff.value:
        found_btn[0] = hwnd
        return False
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumChildWindows(68316, WNDENUMPROC(enum_cb), 0)

btn = found_btn[0]
with open(r"C:\Users\pavlo\golf5\click_res.txt", "w") as f:
    f.write(f"Found btn: {btn}\n")
    if btn:
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        MK_LBUTTON = 0x0001
        lParam = (10 << 16) | 10
        user32.PostMessageW(btn, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
        time.sleep(0.05)
        user32.PostMessageW(btn, WM_LBUTTONUP, 0, lParam)
        f.write("Sent mouse messages to button\n")
