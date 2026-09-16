import struct

with open(r"C:\Users\pavlo\golf5\03G906021QJ_stage1_refined_CS_OK.bin", "rb") as f:
    data = f.read()

# PCR_rBPCtlBas_MAP @ 0x1E9FD0
# Let's inspect A2L entry first
import json
with open(r"C:\Users\pavlo\golf5\diagnostic-review\a2l-characteristics-index.json", "r", encoding="utf-8") as f:
    idx = json.load(f)

for item in idx:
    if "PCR_rBPCtlBas_MAP" in item.get("name", ""):
        addr = int(item["address_hex"], 16)
        size = item["size"]
        layout = item.get("layout")
        print(f"PCR_rBPCtlBas_MAP @ {item['address_hex']}, size={size}, layout={layout}")

offset = 0x1E9FD0
nx, ny = struct.unpack(">HH", data[offset:offset+4])
offset += 4
x_axis = [struct.unpack(">H", data[offset+i*2:offset+i*2+2])[0] for i in range(nx)]
offset += nx * 2
y_axis = [struct.unpack(">H", data[offset+i*2:offset+i*2+2])[0] * 0.01 for i in range(ny)]
offset += ny * 2

print(f"nx={nx}, ny={ny}")
print("X (RPM):", x_axis)
print("Y (IQ):", y_axis)

grid = []
for x in range(nx):
    row = []
    for y in range(ny):
        val = struct.unpack(">H", data[offset:offset+2])[0] * 0.01 # percentage
        offset += 2
        row.append(val)
    grid.append(row)

print(f"\n{'RPM \\ IQ':>8}", end=" | ")
for q in y_axis:
    print(f"{q:>5.0f}", end=" ")
print()
print("-" * (10 + ny * 6))

for x_idx, r in enumerate(x_axis):
    print(f"{r:8d}", end=" | ")
    for y_idx in range(ny):
        print(f"{grid[x_idx][y_idx]:5.1f}", end=" ")
    print()
