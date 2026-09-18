# Reference Dumps & WinOLS Map Packs (VAG 1.9 TDI EDC16)

Збірка еталонних заводських та тюнінгових прошивок (Stage 1, DPF off, EGR off, Hot Start fix), проєктів WinOLS (`.ols`) та карт (`.kp`) для блоків **Bosch EDC16U34 / EDC16U31 / EDC16U1**, двигунів 1.9 TDI (BLS, BXE, BKC, BKE) групи VAG (Volkswagen, Škoda, Seat, Audi).

Джерело: *«Мега сборка тюнинговых прошивок на все марки авто 2019-2020»* (пароль архіву: `veer90`).

---

## 1. Точні збіги для автомобіля (Golf 5 / Jetta 1.9 TDI BLS, HW: `03G906021QJ`, SW: `1037391847` / `1037389289`)

### 1.1 `VW_Jetta_1.9TDI_SW391847_HW03G906021QJ_Stock_and_EGRoff`
* **ECU / Двигун**: Bosch EDC16U34, 1.9 TDI BLS, 105 к.с.
* **Ідентифікатори**:
  * **HW**: `03G906021QJ`
  * **SW**: `1037391847` (SW upg: `03G906021QJ 1984`)
  * **VIN**: `WVWZZZ1KZ8M168447`
* **Файли**:
  * `flashORGIG`: 100% точний заводський сток! Зона калібрувань `0x180000..0x1FDFFF` збігається байт-у-байт із `03G906021QJ_1984_391847_full_stock.bin` (diff = 0 байт).
  * `WinOLS (VW Jetta (egr off_dtc off ) - 391847)`: модифікована версія з відключеним EGR та маскою DTC.
  * `id.txt`: паспортизація блоку.

### 1.2 `VW_Golf5_1.9TDI_SW389289_HW03G906021QJ_Stage1_DPFoff_WinOLS_OLS_KP`
* **ECU / Двигун**: Bosch EDC16U31 / EDC16U34, 1.9 TDI BLS, 105 к.с.
* **Ідентифікатори**:
  * **HW**: `03G906021QJ` (ідентичне «залізо» ECU!)
  * **SW**: `1037389289`
* **WinOLS ресурси**:
  * `WinOLS (VW Golf 5 (Stage 1 DPF off) - 389289).ols`: повний бінарний проєкт WinOLS із розкладеними картами!
  * `WinOLS (VW Golf 5 (Stage 1 DPF off) - 389289).kp`: пакет карт WinOLS Map Pack:
    * `Drivers Wish`
    * `Torque Limit / Smoke Limiter`
    * `Nm to IQ` (конверсія моменту в циклічну подачу)
    * `Boost` (тиск наддуву) & `N75 Duty Cycle`
    * `SOI` (кути випередження впорскування) & `Duration` (тривалість)
    * `Lambda`
    * `Start` & `EGR`
* **Файли калібрувань**:
  * `WinOLS (VW Golf 5 (Stage 1 DPF off) - 389289)`
  * `WinOLS (VW Golf (Low Power) - 389289)`
  * `WinOLS (VW Golf 5 (Stage 1 DPF off no cs) - 389289)`

---

## 2. Споріднені прошивки двигуна BLS 1.9 TDI

### 2.1 `VW_Caddy_1.9TDI_BLS_SW377228_HW03G906021AR_Stage1`
* **ECU / Двигун**: EDC16U34, 1.9 TDI BLS.
* **HW / SW**: `03G906021AR` / `1037377228`.
* **Файли**:
  * `FLASH_ORGINAL`: заводський сток Caddy BLS.
  * `WinOLS (VW Caddy (Imported Version) - 377228)`: Stage 1 тюнінг.
  * `ID.txt`.

### 2.2 `VW_Caddy_1.9TDI_BLS_SW383708_HW03G906021AB_EGRoff`
* **ECU / Двигун**: EDC16U34, 1.9 TDI BLS.
* **HW / SW**: `03G906021AB` / `1037383708`.
* **Файли**:
  * `orginal`: заводський сток.
  * `WinOLS (VW Jetta ( egr off ) - 383708)` (V1, V2, V3 версії EGR off).

---

## 3. Golf 5 / Passat B6 1.9 TDI (EDC16U34 / EDC16U31)

### 3.1 `VW_Golf5_1.9TDI_SW380437_HW03G906021KH_EDC16U34_Stage1`
* **ECU / Двигун**: EDC16U34, 1.9 TDI, HW `03G906021KH`, SW `1037380437`.
* **Файли**: `Golf 5 1.9 TDI Stage 1 Sw 380437 Hw 03G906021KH EDC16U34`, `WinOLS (VW Golf (Stage 1) - 380437)`.

### 3.2 `VW_Golf5_1.9TDI_SW382099_HW03G906021KG_EDC16U31_Stage1`
* **ECU / Двигун**: EDC16U31, 1.9 TDI, HW `03G906021KG`, SW `1037382099`.
* **Файли**: `WinOLS (VW Golf (Stage 1) - 382099)`, `WinOLS (VW Golf (Stage 1 V2) - 382099)`, `WinOLS (VW Passat (Original) - 382088).kp`.

### 3.3 `VW_Golf5_1.9TDI_SW394971_HW03G906021AB_EDC16U31_DPF_EGRoff`
* **ECU / Двигун**: EDC16U31, 1.9 TDI, HW `03G906021AB`, SW `1037394971`.
* **Файли**: `Golf 5 1.9 TDI DPF off EGR off Sw 394971`, `WinOLS (VW Golf (DPF+ EGR off no cs) - 394971).bin`.

### 3.4 `VW_PassatB6_1.9TDI_SW380420_HW03G906021LR_8959_VRPTune_and_Stock`
* **ECU / Двигун**: EDC16U34, 1.9 TDI 105HP, HW `03G906021LR 8959`, SW `1037380420`.
* **Файли**:
  * `Stock/`: заводський чистий файл `Vw Passat 1.9 tdi 105 hp manual SW 1037380420 Upg. SW 03G906021LR 8959`.
  * `Remap/`: тюнінгований файл `VRP Tune` та `WinOLS (VW Passat (stage1) - 380420)`.

### 3.5 `VW_PassatB6_1.9TDI_SW380420_HW03G906021LR_EDC16U34_Stage1`
* **Файли**: `WinOLS (VW Passat (Original) - 380420)`, `WinOLS (VW Passat (maf mod) - 380420)` (калібрування за MAF замість MAP).

---

## 4. Споріднені VAG платформи (Seat, Škoda, Audi)

### 4.1 `Seat_Leon_1.9TDI_SW382081_HW03G906021LK_EDC16U34_EGRoff`
* **ECU**: Bosch EDC16U34 (`0281013279`), HW `03G906021LK`, SW `1037382081`.

### 4.2 `Skoda_Octavia_1.9TDI_SW382414_HW03G906021LB_EDC16U31_Stage1_KP`
* **ECU**: EDC16U31, HW `03G906021LB`, SW `1037382414`.
* **Включає**: оригінальний `.ori`, Stage 1 EGR off, та карту WinOLS `.kp`.

### 4.3 `Skoda_Octavia_1.9TDI_SW371259_HW03G906016DJ_HotStart_DTCoff`
* **ECU**: EDC16U1, HW `03G906016DJ`, SW `1037371259`.
* **Рішення**: виправлення гарячого пуску (Hot Start fix: збільшення пускової подачі на прогрітому моторі) + відключення DTC.

### 4.4 `Audi_A4_1.9TDI_SW390131_HW03G906016FE_EDC16U31_Stage1_KP`
* **ECU**: EDC16U31, HW `03G906016FE`, SW `1037390131`. Включає WinOLS `.kp` map pack.

### 4.5 `Audi_A4_1.9TDI_SW371805_HW03G906016CJ_EDC16U1_Stage1_KP`
* **ECU**: EDC16U1, HW `03G906016CJ`, SW `1037371805`. Включає 2 версії VRP Tune + WinOLS `.kp`.

### 4.6 `Audi_A3_1.9TDI_SW371093_HW0281011832_EDC16U1_Stage1_KP`
* **ECU**: EDC16U1, SW `1037371093`. Включає WinOLS `.kp` map pack.
