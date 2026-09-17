import time
import ctypes
from PIL import ImageGrab

user32 = ctypes.windll.user32

# Hwnd 3016528 is MPPS
hwnd = 3016528
user32.ShowWindow(hwnd, 9) # SW_RESTORE
user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
user32.SetForegroundWindow(hwnd)
user32.BringWindowToTop(hwnd)

time.sleep(1)
im = ImageGrab.grab()
im.save(r"C:\Users\pavlo\golf5\mpps_main_window.png")
