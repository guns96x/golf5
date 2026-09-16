import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a2l_path = 'diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l'
with open(a2l_path, 'r', encoding='latin-1') as f:
    content = f.read()

name = 'AccPed_trqEngLim_MAP'
pattern = rf'/begin CHARACTERISTIC\s+{re.escape(name)}\b(.*?)/end CHARACTERISTIC'
match = re.search(pattern, content, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("NOT FOUND")
