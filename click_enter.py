import time
import ctypes

user32 = ctypes.windll.user32

hwnd = 68316
user32.ShowWindow(hwnd, 9) # SW_RESTORE
user32.SetForegroundWindow(hwnd)
user32.BringWindowToTop(hwnd)

time.sleep(0.5)

# keybd_event VK_RETURN = 0x0D
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002

user32.keybd_event(VK_RETURN, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

time.sleep(1)
