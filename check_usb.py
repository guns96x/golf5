import os, glob
print('Checking USB devices in /dev/bus/usb:')
for p in glob.glob('/dev/bus/usb/*/*'):
    r = os.access(p, os.R_OK)
    w = os.access(p, os.W_OK)
    print(f'{p}: read={r} write={w}')
