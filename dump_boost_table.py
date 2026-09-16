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

print(f"nx={nx}, ny={ny}")
print("X (RPM):", x_axis)
print("Y (IQ):", y_axis)

# Print as 2D grid
grid = []
for y in range(ny):
    row = []
    for x in range(nx):
        val = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        row.append(val)
    grid.append(row)

# Print header
print(f"\n{'IQ \\ RPM':>8}", end=" | ")
for r in x_axis:
    print(f"{r:>5}", end=" ")
print()
print("-" * (10 + nx * 6))

for y_idx, y in enumerate(y_axis):
    print(f"{y:8.1f}", end=" | ")
    for x_idx in range(nx):
        print(f"{grid[y_idx][x_idx]:5d}", end=" ")
    print()
