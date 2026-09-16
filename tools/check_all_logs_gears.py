import glob
import os

files = glob.glob('logs/20260916/Turbo_Pair_*.csv')

for f in sorted(files):
    with open(f, 'r') as fp:
        lines = [line.strip().split(',') for line in fp if line.strip()]
    if len(lines) < 2:
        continue
    header = lines[0]
    h_map = {h: i for i, h in enumerate(header)}
    
    wot_points = []
    for row in lines[1:]:
        if len(row) < len(header):
            continue
        try:
            load = float(row[h_map['load_pct']]) if row[h_map['load_pct']] else 0.0
            rpm = float(row[h_map['rpm']]) if row[h_map['rpm']] else 0.0
            speed = float(row[h_map['speed_kmh']]) if row[h_map['speed_kmh']] else 0.0
            map_val = float(row[h_map['map_mbar_abs']]) if row[h_map['map_mbar_abs']] else 0.0
            if load >= 90.0:
                ratio = speed / rpm if rpm > 0 else 0
                wot_points.append((rpm, speed, ratio, map_val))
        except (ValueError, IndexError):
            continue
    if wot_points:
        rpms = [p[0] for p in wot_points]
        speeds = [p[1] for p in wot_points]
        ratios = [p[2] for p in wot_points]
        avg_ratio = sum(ratios) / len(ratios)
        # Golf 5 BLS 5-speed 0A4 manual approximate km/h per 1000 rpm:
        # Gear 1: ~8.5 km/h / 1000 rpm (ratio ~0.0085)
        # Gear 2: ~15.5 km/h / 1000 rpm (ratio ~0.0155)
        # Gear 3: ~24.5 km/h / 1000 rpm (ratio ~0.0245)
        # Gear 4: ~34.5 km/h / 1000 rpm (ratio ~0.0345)
        # Gear 5: ~46.0 km/h / 1000 rpm (ratio ~0.0460)
        est_gear = "Unknown"
        if 0.020 <= avg_ratio < 0.029:
            est_gear = "Gear 3"
        elif 0.030 <= avg_ratio < 0.040:
            est_gear = "Gear 4"
        elif 0.041 <= avg_ratio < 0.055:
            est_gear = "Gear 5"
        print(f"{os.path.basename(f):<32} WOT pts={len(wot_points):<3} RPM: {min(rpms):.0f}..{max(rpms):.0f} Speed: {min(speeds):.0f}..{max(speeds):.0f} km/h Ratio={avg_ratio:.4f} -> {est_gear}")
    else:
        print(f"{os.path.basename(f):<32} No WOT points (>=90% load)")
