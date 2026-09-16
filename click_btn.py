import time
import ctypes

user32 = ctypes.windll.user32

# Find the button with text 'OK' under window with title 'Mpps'
def find_btn(parent):
    btn_hwnd = [0]
    def child_cb(hwnd, lparam):
        cls_buff = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buff, 256)
        txt_buff = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, txt_buff, 256)
        if cls_buff.value == "Button" and "OK" in txt_buff.value:
            btn_hwnd[0] = hwnd
            return False
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumChildWindows(parent, WNDENUMPROC(child_cb), 0)
    return btn_hwnd[0]

btn = find_btn(68316)
print("Found button:", btn)
if btn:
    # Send BM_CLICK = 0x00F5
    user32.SendMessageW(btn, 0x00F5, 0, 0)
    print("Sent BM_CLICK")

time.sleep(2)
