import struct

with open(r"C:\Users\pavlo\golf5\03G906021QJ_stage1_refined_CS_OK.bin", "rb") as f:
    data = f.read()

offset = 0x1EB0B2
nx, ny = struct.unpack(">HH", data[offset:offset+4])
offset += 4
x_axis = [struct.unpack(">H", data[offset+i*2:offset+i*2+2])[0] for i in range(nx)]
offset += nx * 2
y_axis = [struct.unpack(">H", data[offset+i*2:offset+i*2+2])[0] * 0.01 for i in range(ny)]
offset += ny * 2

# Transposed: 16 RPMs as rows, 10 IQs as columns
grid = []
for x in range(nx):
    row = []
    for y in range(ny):
        val = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        row.append(val)
    grid.append(row)

print(f"{'RPM \\ IQ':>8}", end=" | ")
for q in y_axis:
    print(f"{q:>5.0f}", end=" ")
print()
print("-" * (10 + ny * 6))

for x_idx, r in enumerate(x_axis):
    print(f"{r:8d}", end=" | ")
    for y_idx in range(ny):
        print(f"{grid[x_idx][y_idx]:5d}", end=" ")
    print()
