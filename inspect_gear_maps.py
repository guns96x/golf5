import struct

f_bin = r"C:\Users\pavlo\golf5\03G906021QJ_stage1_refined_CS_OK.bin"
with open(f_bin, "rb") as f:
    data = f.read()

# Let's inspect AccPed maps:
# 0x1C2CCE: AccPed_trqEng0_MAP (Gear 1 / General)
# 0x1C2E24: AccPed_trqEng1_MAP (Gear 2)
# 0x1C2F7A: AccPed_trqEng2_MAP (Gear 3)
# 0x1C30D0: AccPed_trqEng3_MAP (Gear 4)

def dump_map_header(addr, name):
    # EDC16 maps usually have axis sizes preceding or embedded
    sub = data[addr:addr+342]
    # Let's print min and max 16-bit values in the map area
    vals = [struct.unpack(">h", sub[i:i+2])[0] * 0.1 for i in range(0, min(len(sub), 200), 2)]
    print(f"{name} @ 0x{addr:X}: max = {max(vals):.1f} Nm, min = {min(vals):.1f} Nm")

dump_map_header(0x1C2CCE, "AccPed Gear 1 (0)")
dump_map_header(0x1C2E24, "AccPed Gear 2 (1)")
dump_map_header(0x1C2F7A, "AccPed Gear 3 (2)")
dump_map_header(0x1C30D0, "AccPed Gear 4 (3)")

# Torque limiter: EngPrt_trqLimP_MAP @ 0x1D4732
sub_tl = data[0x1D4732:0x1D4732+102]
vals_tl = [struct.unpack(">h", sub_tl[i:i+2])[0] * 0.1 for i in range(0, len(sub_tl), 2)]
print(f"Torque Limiter @ 0x1D4732: max = {max(vals_tl):.1f} Nm, min = {min(vals_tl):.1f} Nm")
