import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a2l_path = 'diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l'
with open(a2l_path, 'r', encoding='latin-1') as f:
    content = f.read()

matches = re.findall(r'InjVlv_phiInjMI1_MAP\d', content)
print("Unique InjVlv maps mentioned:", sorted(set(matches)))

# Find any characteristics or measurements starting with InjVlv
for m in re.finditer(r'/begin CHARACTERISTIC\s+(InjVlv_[^\s]+)\s+"([^"]+)"', content):
    print(f"{m.group(1):<30}: {m.group(2)}")

