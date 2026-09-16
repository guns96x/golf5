# Code-gate audit: `EGT_swtEGTActv_C` / EDC16U34 SW 391847

Дата: 2026-09-10. Робота read-only; BIN/HEX/S19/SGM/A2L не змінювалися і нічого не прошивалося.

## Короткий результат

Точне твердження «`EGT_swtEGTActv_C=0` вимикає всі шляхи регенерації, EGT-захисту та післявпорскування» з доступних матеріалів **не доводиться**. A2L надійно дає адресу, тип, назву підсистеми та вимірювальні точки, а HEX/S19-derived reference дає кодову область для аналізу. Але обидва надані користувацькі BIN мають `FF` у всьому префіксі `0x000000–0x17FFFF`, де лежить код; тому їхній реальний виконуваний код не можна зіставити з reference. Без цього зіставлення і без PowerPC-дизассемблера/графа викликів немає exact-code proof.

## Що саме підтверджує A2L

- `EGT_swtEGTActv_C` — `VALUE`, адреса `0x1D4274`, тип `Kw_Wu8`, діапазон 0..1 (`...a2l:242329-242340`). У provided ON byte `01`, у provided OFF byte `00`; це однобайтовий gate, а не BE-слово `0x0100`.
- A2L групує цей параметр у функцію `EGT_CoRgn`, описану як координатор регенерації aftertreatment (`...a2l:718895-718901`). Це сильний доказ призначення/архітектурного контексту, але FUNCTION-блоки не містять адреси машинного коду або call graph.
- Окремо описані `PFlt_CoRgn`/`PFlt_CoRgn2`; `PFlt_numEngPOp1_CA` належить до `PFlt_CoRgn2` (`...a2l:721733-721757`). A2L задає його як 8×8 `Kf_Xu8_Yu8_Wu8` на `0x1ECA6E` (`...a2l:405546-405611`). Надане OFF справді зануляє 64 value-byte (29 байтів змінено від ON), але це тільки одна таблиця стану регенерації.
- Для післявпорскування A2L має окремі функціональні групи `InjCrv_PoI2`, `InjCrv_PoI2Lmbd`, `InjCrv_PoI2TPst` та `InjCrv_PoI2Q` (`...a2l:720714-720735`, `...a2l:720739-720755`). Це доводить наявність окремих PoI2-гілок/калібрувань, але не те, що вони всі залежать від одного gate.
- Найкорисніші runtime hooks: `EGT_swtEGTActv` описаний як message для деактивації всієї aftertreatment-функціональності, ECU address `0x7F93AF` (`...a2l:577216-577230`); `EGSys_qPoIRgn` — пізня післявпорскана кількість, `0x7F9888` (`...a2l:572814-572833`); `InjCrv_qPoI2Des` — задана кількість PoI2, `0x7F9A84` (`...a2l:647440-647454`); `PFlt_stMonRgnActv_mp` — статус regeneration active, `0x9FFF77` (`...a2l:683228-683242`). Це точки для runtime-лога, не доказ виконання у BIN.

## Bounded xref / lookup audit у повному reference

Повний `diagnostic-review/reference-from-hex.analysis-only.bin` починається з PowerPC-подібного big-endian вектора (`48 00 13 C3 ...`), а A2L називає CPU `SilverOak` (`...a2l:1046`). Read-only скан 32-бітних big-endian слів дав такі входження literal `0x001D4274`:

| Offset у reference | Спостереження | Інтерпретація |
|---:|---|---|
| `0x04CCA0` | усередині довгого зростаючого списку A2L-адрес; поруч `0x1D3894`, `0x1D389A`, `0x1D3BB8`, `0x1D4270`, `0x1D427C` | lookup/address table, не доведений code consumer |
| `0x180330` | такий самий список | копія/зарезервований display/lookup-блок |
| `0x180938` | такий самий список | копія/зарезервований display/lookup-блок |
| `0x180F40` | такий самий список | копія/зарезервований display/lookup-блок |

Інших прямих literal-входжень `0x001D4274` у reference немає. Для порівняння, `0x007F9A84` (`InjCrv_qPoI2Des`) трапляється в address/measurement table за `0x048EBC`, а `0x007F9C3A` (`PFlt_tPre`) — за `0x0479D4` і `0x048790`; це також таблиці описів/measurement pointers, а не доведені виклики. Сам факт pointer-table entry не встановлює, хто і за яких умов читає значення.

У reference A2L визначає executable ranges `0x101E8–0x37E7B`, `0x40058–0x9FF77`, `0xA0000–0x17FF77` як CODE (`...a2l:1063-1070`, `1108-1115`, `1138-1145`). У користувацьких ON/OFF ці діапазони заповнені `FF`; отже, observed lookup entries та будь-які функції з reference не можна переносити на виконуваний код встановленого ECU. `reference-from-hex.analysis-only.bin` — лише аналітичний reference, не validated flash image.

## SGM і межі integrity/checksum доказу

SGM — XML/MIME контейнер Bosch/VW, не plain executable image. Він містить такі блоки:

| SGM block | Physical range | Declared decompressed size | Check-covered range | Container checksum field |
|---|---:|---:|---:|---:|
| `dav_pfu_01` | `0x10000–0x3FFFF` | `0x2FF00` | `0x10000–0x3FEFF` | `0x8F04` |
| `dav_pfu_02` | `0x40000–0x17FFFF` | `0x140000` | `0x40000–0x17FFFF` | `0x225D` |
| `dav_pfu_05` | `0x180000–0x1BFFFF` | `0x40000` | `0x180000–0x1BFFFF` | `0xEE55` |
| `dav_pfu_04` | `0x1C0000–0x1FFFFF` | `0x3E000` | `0x1C0000–0x1FDFFF` | `0x73BA` |

Evidence is in SGM tags at lines `69-81`, `3733-3745`, `28033-28045`, `32763-32775`. Base64 decoding yields payloads with exactly the declared sizes, but payload bytes do not equal the HEX/S19-derived physical ranges and no standard zlib/gzip/bz2/lzma decode succeeded. Therefore the SGM payload was not treated as disassembled code; its MIME/format-02 transform is not identified here.

A2L does expose integrity metadata, but not the algorithm implementation:

- ETK `CODE_CHK` stores the program identifier at mapped address `0x11FDF74`, length 4, with external-RAM mirror at `0x9FFFF8` (`...a2l:4765-4769`). Because DATA mapping is physical `0x1C0000 -> 0x11C0000`, this corresponds to physical `0x1FDF74`. The four bytes are `21 3F EC 5D` in reference, ON and OFF; this only says the visible program identifier was unchanged, not that the modified calibration has been checksum-accepted.
- KWP2000 checksum metadata is qualifier `0x010201`, active-page `1`, local routine `1`, result mode `RequestRoutineResults`, result code `0x23` (`...a2l:4811-4817`). MCMESS has type qualifier `0x8001`, `CHECKSUM_CALCULATION ACTIVE_PAGE` (`...a2l:4902-4905`). Neither block supplies a Bosch checksum DLL/algorithm or proves any file is flashable.
- No local `objdump`/radare2/rizin/Ghidra/IDA/Capstone/Bosch checksum utility/WinOLS/VAGEDCSuite/ZedSuite executable was found on PATH. The installed LLVM 22 `llvm-objdump.exe` is present at `C:\Program Files\LLVM\bin`, but its registered targets omit PowerPC; it cannot be used as a valid disassembler for this image without adding a tool.

## The two unmatched trailers

The newly noted ON-vs-reference unmatched ranges are exactly boundary/reserved areas:

- `0x1BFF74–0x1BFFFF` (140 bytes) is the tail of A2L `Pst180000`, `RESERVED FLASH`, `0x180000`, length `0x40000` (`...a2l:1168-1175`).
- `0x1FDF78–0x1FDFFF` (136 bytes) is A2L `Dst1FDF78`, `RESERVED FLASH`, length `0x88` (`...a2l:1213-1220`), immediately following the physical code-check identifier at `0x1FDF74`.

Neither range overlaps an A2L CHARACTERISTIC. The first contains repeated pointer/lookup structures elsewhere in its reserved block; the second is adjacent to the explicit code identifier. They are therefore best classified as reserved/display/integrity metadata candidates, not calibration maps. Their byte differences must not be “fixed” or interpreted as checksum values without the ECU-specific routine. The SGM block checks (`0xEE55`, `0x73BA`) are container metadata and do not validate these trailers or the Bosch internal checksum.

## Verdict and concrete blocker

Available A2L + full reference allow **architectural and bounded lookup reasoning**:

`EGT_CoRgn` → `EGT_swtEGTActv_C` (calibration gate) is associated with aftertreatment regeneration; `PFlt_CoRgn2` → `PFlt_numEngPOp1_CA` is one regeneration operating-state matrix; PoI2 has multiple separately named functions/maps and direct measurement hooks.

They do **not** allow exact-code reasoning that `EGT_swtEGTActv_C=0` disables every regen/post-injection/thermal branch, because the executable code is absent from both user BINs and the local disassembler/toolchain cannot decode the PowerPC code in the reference. The user's heat/load-dependent symptom observations (including recurrence with emissions ON during regeneration and EGR now physically blanked) are valuable diagnostic clues, but do not repair this static-code gap or prove current OFF runtime behavior.

Required evidence to close the gate is one of: (1) verified full ECU readback containing the same code region plus exact ECU/SW identity, then PowerPC disassembly and call/data-flow review; or (2) runtime log from the installed ECU showing `EGT_swtEGTActv`, `PFlt_stMonRgnActv_mp`, `InjCrv_qPoI2Des`, `EGSys_qPoIRgn`, relevant EGT values and status under the reproducible heat/load event. Do not use this report to produce a flash file, recalculate trailers, or claim checksum validity.
