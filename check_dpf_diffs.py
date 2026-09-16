import json

with open(r"C:\Users\pavlo\golf5\diagnostic-review\binary-comparison.json", "r", encoding="utf-8") as f:
    comp = json.load(f)

with open(r"C:\Users\pavlo\golf5\diagnostic-review\a2l-characteristics-index.json", "r", encoding="utf-8") as f:
    idx = json.load(f)

ranges = comp.get("ranges", [])
print(f"Total diff ranges between ON and OFF: {len(ranges)}")

for r in ranges:
    start_hex = r["start"]
    start = int(start_hex, 16)
    length = r["length"]
    # match against A2L
    matches = []
    for item in idx:
        addr = int(item.get("address_hex", "0"), 16)
        size = item.get("size", 0)
        if addr <= start < addr + max(size, 1) or start <= addr < start + length:
            matches.append(item.get("name"))
    match_str = ", ".join(matches) if matches else "Unmapped"
    print(f"Range {start_hex} (len {length}): {match_str}")
