import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a2l_path = 'diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l'
with open(a2l_path, 'r', encoding='latin-1') as f:
    content = f.read()

for m in re.finditer(r'/begin CHARACTERISTIC\s+([a-zA-Z0-9_]+)\s+"([^"]*)"\s+([A-Z_]+)\s+(0x[0-9A-Fa-f]+)', content):
    name, desc, kind, addr = m.groups()
    if kind in ['MAP', 'CURVE']:
        if any(k in name.lower() for k in ['gear', 'gang']) or any(k in desc.lower() for k in ['gang', 'gear']):
            print(f"{name:<35} {kind:<8} {addr:<10} {desc[:50]}")

