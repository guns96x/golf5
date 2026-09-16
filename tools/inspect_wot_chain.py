import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/a2l-characteristics-index.json', 'r', encoding='utf-8') as f:
    chars = json.load(f)

with open('diagnostic-review/a2l-characteristics-index.json', 'r', encoding='utf-8') as f:
    chars = json.load(f)

print("=== ALL TORQUE MAPS/CURVES ===")
for c in chars:
    n = c.get('name', '')
    d = c.get('description', '')
    kind = c.get('kind', '')
    if kind in ['MAP', 'CURVE']:
        if any(w in n.lower() for w in ['trq', 'torque', 'moment', 'drehmoment']) or any(w in d.lower() for w in ['drehmoment', 'torque']):
            print(f"{n:<35} {kind:<8} {c.get('address_hex',''):<10} {c.get('layout',''):<18} {d[:45]}")


