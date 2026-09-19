import time
import ctypes
from PIL import ImageGrab

user32 = ctypes.windll.user32

# Close modal dialog 199332
user32.PostMessageW(199332, 0x0010, 0, 0) # WM_CLOSE
user32.PostMessageW(330440, 0x00F5, 0, 0) # BM_CLICK

time.sleep(1)

# Now show main window 3016528
user32.ShowWindow(3016528, 9) # SW_RESTORE
user32.ShowWindow(3016528, 3) # SW_MAXIMIZE
user32.SetForegroundWindow(3016528)
user32.BringWindowToTop(3016528)

time.sleep(1)
im = ImageGrab.grab()
im.save(r"C:\Users\pavlo\golf5\mpps_active.png")
print("Captured mpps_active.png")
