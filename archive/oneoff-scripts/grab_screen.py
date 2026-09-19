from PIL import ImageGrab
im = ImageGrab.grab()
im.save(r"C:\Users\pavlo\golf5\full_screen.png")
print("Saved full_screen.png:", im.size)
