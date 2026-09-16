"""Read-only comparison of supplied ECU images; does not validate ECU checksums."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
ASSETS = Path(r"\\?\C:\Users\pavlo\.cloudcli\assets")
a_path = next(ASSETS.glob("1789027452850-*"))
b_path = ROOT / "extracted" / "03G906021QJ (DPF EGR OFF) NoCS.Bin"
a, b = a_path.read_bytes(), b_path.read_bytes()

def identify(data):
    return {
        "length": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "identifiers": [
            {"offset": hex(m.start()), "text": m.group().decode("ascii")}
            for m in re.finditer(rb"[ -~]{8,}", data)
            if re.search(rb"03G906|103739|R4 1,9|EDC16|BOSCH", m.group())
        ],
        "ff_bytes": data.count(255),
        "zero_bytes": data.count(0),
    }

diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
ranges = []
for i in diff:
    if ranges and i == ranges[-1][1] + 1:
        ranges[-1][1] = i
    else:
        ranges.append([i, i])

report = {
    "supplied_first": identify(a),
    "archive_image": identify(b),
    "equal_lengths": len(a) == len(b),
    "differing_bytes": len(diff),
    "contiguous_differing_ranges": len(ranges),
    "changed_64KiB_blocks": [
        {"start": hex(start), "end": hex(start + 65535),
         "differing_bytes": sum(x != y for x, y in zip(a[start:start+65536], b[start:start+65536]))}
        for start in range(0, min(len(a), len(b)), 65536)
        if a[start:start+65536] != b[start:start+65536]
    ],
    "ranges": [
        {"start": hex(s), "end": hex(e), "length": e-s+1,
         "first_hex": a[s:e+1].hex(" ") if e-s < 64 else a[s:s+32].hex(" ") + " ...",
         "archive_hex": b[s:e+1].hex(" ") if e-s < 64 else b[s:s+32].hex(" ") + " ..."}
        for s, e in ranges
    ],
    "limitations": [
        "No verified stock reference or calibration definitions supplied.",
        "No ECU-specific checksum validation performed.",
        "Neither image confirmed as currently installed.",
        "Byte differences alone do not establish map functions, successful DPF/EGR deactivation or symptom cause."
    ]
}
(ROOT / "binary-comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
summary = {k: v for k, v in report.items() if k != "ranges"}
summary["first_30_ranges"] = report["ranges"][:30]
print(json.dumps(summary, indent=2))
