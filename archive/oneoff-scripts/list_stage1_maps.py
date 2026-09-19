import json
with open(r'C:\Users\pavlo\golf5\diagnostic-review\stage1-map-review.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for c in data['changed_characteristics']:
    name = c['name']
    addr = c['address_hex']
    cb = c['changed_bytes']
    print(f"{name} @ {addr} ({cb} bytes)")
