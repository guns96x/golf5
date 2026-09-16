import glob
import os
import statistics

files = glob.glob('logs/20260916/Turbo_Pair_*.csv')

def classify_ratio(r):
    # Golf 5 BLS 5-speed 0A4 manual (0.0330..0.0375 is Gear 4)
    if 0.0210 <= r <= 0.0285:
        return "Gear 3 (21-28 km/h / 1000 rpm)"
    elif 0.0320 <= r <= 0.0380:
        return "Gear 4 (32-38 km/h / 1000 rpm)"
    elif 0.0420 <= r <= 0.0520:
        return "Gear 5 (42-52 km/h / 1000 rpm)"
    elif 0.0130 <= r <= 0.0195:
        return "Gear 2 (13-19 km/h / 1000 rpm)"
    elif 0.0070 <= r <= 0.0120:
        return "Gear 1 (7-12 km/h / 1000 rpm)"
    return "Indeterminate"

print(f"{'Filename':<32} {'Fresh Pts':<10} {'RPM range':<14} {'Speed range':<14} {'Median Ratio':<13} {'MAD':<9} {'Classification'}")
print("-" * 115)

for f in sorted(files):
    with open(f, 'r') as fp:
        lines = [line.strip().split(',') for line in fp if line.strip()]
    if len(lines) < 2:
        continue
    header = lines[0]
    h_map = {h: i for i, h in enumerate(header)}
    
    valid_samples = []
    for line_idx, row in enumerate(lines[1:], 1):
        if len(row) < len(header):
            continue
        try:
            load = float(row[h_map['load_pct']]) if row[h_map['load_pct']] else 0.0
            rpm = float(row[h_map['rpm']]) if row[h_map['rpm']] else 0.0
            speed = float(row[h_map['speed_kmh']]) if row[h_map['speed_kmh']] else 0.0
            speed_age = float(row[h_map['speed_age_ms']]) if row[h_map['speed_age_ms']] else 999999.0
            
            # Robust criteria: WOT, engine running >1200 RPM, speed updated within 1000ms, moving vehicle
            if load >= 90.0 and rpm > 1200.0 and speed_age <= 1000.0 and speed > 10.0:
                ratio = speed / rpm
                valid_samples.append({
                    'rpm': rpm,
                    'speed': speed,
                    'speed_age': speed_age,
                    'ratio': ratio
                })
        except (ValueError, IndexError):
            continue
            
    if not valid_samples:
        print(f"{os.path.basename(f):<32} No fresh WOT samples (load>=90%, rpm>1200, speed_age<=1000ms)")
        continue
        
    rpms = [s['rpm'] for s in valid_samples]
    speeds = [s['speed'] for s in valid_samples]
    ratios = [s['ratio'] for s in valid_samples]
    med_ratio = statistics.median(ratios)
    mad = statistics.median([abs(r - med_ratio) for r in ratios])
    gear_class = classify_ratio(med_ratio)
    rpm_str = f"{min(rpms):.0f}..{max(rpms):.0f}"
    speed_str = f"{min(speeds):.0f}..{max(speeds):.0f} km/h"
    print(f"{os.path.basename(f):<32} {len(valid_samples):<10} {rpm_str:<14} {speed_str:<14} {med_ratio:<13.4f} {mad:<9.5f} {gear_class}")

