with open(r"C:\Users\pavlo\golf5\diagnostic-review\a2l-characteristics-index.json", "r", encoding="utf-8") as f:
    import json
    idx = json.load(f)

for item in idx:
    if item.get("name") == "PCR_pBDesBas_MAP":
        print(item)
