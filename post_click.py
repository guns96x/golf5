import time
import ctypes

user32 = ctypes.windll.user32

btn = 68346

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

# lParam = (y << 16) | x  (local coordinates inside button, say (10, 10))
lParam = (10 << 16) | 10

user32.PostMessageW(btn, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
time.sleep(0.05)
user32.PostMessageW(btn, WM_LBUTTONUP, 0, lParam)

time.sleep(1)
