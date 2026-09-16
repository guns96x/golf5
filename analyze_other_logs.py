import csv

for path in [
    r"C:\Users\pavlo\golf5\logs\VCDS_WOT_Log_20260914_122626.csv",
    r"C:\Users\pavlo\golf5\logs\VCDS_WOT_Log_20260914_114936.csv"
]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"\nFile: {path.split('\\')[-1]}, rows={len(rows)}")
    pulls = [r for r in rows if float(r.get("RPM", 0) or 0) > 1300 and float(r.get("Boost_Specified_mbar", 0) or 0) > 1500]
    print(f"High load points: {len(pulls)}")
    if pulls:
        max_act = max(float(r["Boost_Actual_mbar"]) for r in pulls)
        max_req = max(float(r["Boost_Specified_mbar"]) for r in pulls)
        print(f"Max Req: {max_req:.0f}, Max Act: {max_act:.0f}")
