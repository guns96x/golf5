import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a2l_path = 'diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l'
with open(a2l_path, 'r', encoding='latin-1') as f:
    content = f.read()

for m in re.finditer(r'/begin CHARACTERISTIC\s+(AccPed_trqEng[0-9a-zA-Z_]+)\s+"([^"]+)"', content):
    print(f"{m.group(1):<25}: {m.group(2)}")
