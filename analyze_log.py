import csv

log_path = r"C:\Users\pavlo\golf5\logs\VCDS_WOT_Log_20260914_153242.csv"
with open(log_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total data points: {len(rows)}")

# Find max RPM, max boost, max IQ
rpms = [float(r["RPM"]) for r in rows if r["RPM"]]
boost_reqs = [float(r["Boost_Specified_mbar"]) for r in rows if r["Boost_Specified_mbar"]]
boost_acts = [float(r["Boost_Actual_mbar"]) for r in rows if r["Boost_Actual_mbar"]]
n75s = [float(r["N75_Duty_pct"]) for r in rows if r["N75_Duty_pct"]]

print(f"RPM range: {min(rpms):.0f} - {max(rpms):.0f}")
print(f"Boost Req range: {min(boost_reqs):.0f} - {max(boost_reqs):.0f} mbar")
print(f"Boost Act range: {min(boost_acts):.0f} - {max(boost_acts):.0f} mbar")
print(f"N75 Duty range: {min(n75s):.1f}% - {max(n75s):.1f}%")

print("\n--- Rows where RPM > 1200 (Acceleration pull) ---")
pull_rows = [r for r in rows if float(r["RPM"]) > 1200]
print(f"Acceleration points count: {len(pull_rows)}")
for r in pull_rows:
    t = float(r["RelativeTime_s"])
    rpm = float(r["RPM"])
    req = float(r["Boost_Specified_mbar"])
    act = float(r["Boost_Actual_mbar"])
    diff = act - req
    n75 = float(r["N75_Duty_pct"])
    print(f"T={t:6.2f}s | RPM={rpm:4.0f} | Req={req:4.0f} | Act={act:4.0f} | Diff={diff:+5.0f} | N75={n75:4.1f}%")
