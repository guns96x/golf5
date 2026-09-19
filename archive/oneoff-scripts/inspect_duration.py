import struct

f_ideal = r"C:\Users\pavlo\golf5\03G906021QJ_ideal_stage1_dpf_egr_off.bin"
f_refined = r"C:\Users\pavlo\golf5\03G906021QJ_stage1_refined_CS_OK.bin"

with open(f_ideal, "rb") as f1, open(f_refined, "rb") as f2:
    b1 = f1.read()
    b2 = f2.read()

# InjVlv_phiInjMI1_MAP1 @ 0x1E5032
# Size is around 10x10 or 10x15 words
sub1 = [struct.unpack(">H", b1[i:i+2])[0] * 0.0234375 for i in range(0x1E5032, 0x1E5032+100, 2)]
sub2 = [struct.unpack(">H", b2[i:i+2])[0] * 0.0234375 for i in range(0x1E5032, 0x1E5032+100, 2)]

print("InjVlv Duration 0 max in ideal:  ", max(sub1))
print("InjVlv Duration 0 max in refined:", max(sub2))

diff_count = sum(1 for a, b in zip(sub1, sub2) if a != b)
print("Differences in first 50 words:", diff_count)
for i in range(min(len(sub1), 20)):
    if sub1[i] != sub2[i]:
        print(f"[{i}] ideal: {sub1[i]:.2f} deg, refined: {sub2[i]:.2f} deg")
