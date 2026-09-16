import time
import ctypes

user32 = ctypes.windll.user32

hwnd = 68316
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
user32.BringWindowToTop(hwnd)

time.sleep(0.5)

x = 904
y = 442

user32.SetCursorPos(x, y)
time.sleep(0.1)

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

user32.mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
time.sleep(0.05)
user32.mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, 0)

time.sleep(1)
