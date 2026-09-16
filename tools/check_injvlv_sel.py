import re
import struct
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a2l_path = 'diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l'
with open(a2l_path, 'r', encoding='latin-1') as f:
    content = f.read()

m = re.search(r'/begin CHARACTERISTIC\s+InjVlv_numMI1_CUR\b(.*?)/end CHARACTERISTIC', content, re.DOTALL)
if m:
    print(m.group(0))

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

addr_m = re.search(r'0x[0-9A-Fa-f]+', m.group(0))
if addr_m:
    addr = int(addr_m.group(0), 16)
    print(f"Address: {hex(addr)}")
    nx = struct.unpack_from('>h', stg_bin, addr)[0]
    print(f"nx: {nx}")
    x_axis = struct.unpack_from('>' + str(nx) + 'h', stg_bin, addr + 2)
    vals = struct.unpack_from('>' + str(nx) + 'h', stg_bin, addr + 2 + 2*nx)
    print("X axis (raw):", x_axis)
    print("Vals (raw):", vals)
