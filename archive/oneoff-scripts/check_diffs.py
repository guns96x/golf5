import json

with open(r'C:\Users\pavlo\golf5\diagnostic-review\a2l-characteristics-index.json', 'r', encoding='utf-8') as f:
    idx = json.load(f)

targets = [0x1D6603, 0x1DADCF, 0x1F0762]
for item in idx:
    addr = int(item.get('address', '0'), 16) if isinstance(item.get('address'), str) else item.get('address', 0)
    for t in targets:
        if abs(addr - t) < 300:
            print(f"{item.get('name')} @ 0x{addr:X} (near 0x{t:X})")
