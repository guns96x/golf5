import struct

f_ref = r"C:\Users\pavlo\golf5\03G906021QJ_stage1_refined_CS_OK.bin"
with open(f_ref, "rb") as f:
    data = f.read()

# PCR_pBDesBas_MAP @ 0x1EB0B2
# Header: 16x10
# X axis: 16 RPM words
# Y axis: 10 IQ words
# Z data: 16x10 = 160 words
offset = 0x1EB0B2
nx, ny = struct.unpack(">HH", data[offset:offset+4])
offset += 4
x_axis = [struct.unpack(">H", data[offset+i*2:offset+i*2+2])[0] for i in range(nx)]
offset += nx * 2
y_axis = [struct.unpack(">H", data[offset+i*2:offset+i*2+2])[0] * 0.01 for i in range(ny)]
offset += ny * 2

print(f"Map size: {nx} x {ny}")
print("RPM axis:", x_axis)
print("IQ axis (mg):", y_axis)

z_vals = []
for y_idx in range(ny):
    row = []
    for x_idx in range(nx):
        val = struct.unpack(">H", data[offset:offset+2])[0]
        row.append(val)
        offset += 2
    z_vals.append(row)

print("\nBoost target at max IQ (last row):")
for r, val in zip(x_axis, z_vals[-1]):
    print(f"{r} RPM -> {val} mbar")
