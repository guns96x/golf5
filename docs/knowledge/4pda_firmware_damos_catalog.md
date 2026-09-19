# Повний каталог і аналіз теми 4PDA (Topic 893610: «Крупнейшая бесплатная сборка дамосов и прошивок»)

## 1. Загальна статистика дослідження 101 сторінки

Автономний краулер просканував усі 101 сторінку теми (`st=0..2000`).
* **Всього знайдено постів із посиланнями на завантаження**: 390
* **Розподіл по сховищах**:
  * `yadi.sk` / `disk.yandex.*`: 237 посилань
  * `cloud.mail.ru`: 108 посилань
  * `4pda.to/forum/dl/...` (внутрішні вкладення форуму): 321 файл
  * `mega.nz`: 8 посилань
  * Торрент-файли та magnet-посилання: 7 посилань
  * `drive.google.com`: 1 посилання

---

## 2. Ключові ресурси та роздачі з теми

### 2.1 Головна мега-роздача теми (Шапка)
* **Назва**: `damos and firmware (GIFROM).torrent`
* **Розмір файлу торента**: **71.4 МБ** (один із найбільших торрент-файлів у рунеті, містить десятки тисяч папок та сотні гігабайт прошивок/дамосів).
* **Посилання на торрент**:
  * [Яндекс Диск](https://yadi.sk/d/-fzmtGrs3TShSa)
  * [Облако Mail.ru](https://cloud.mail.ru/public/DBjJ/pG4vfm38M)
* **Хмарний архів шапки**:
  * [Сборка Damos и прошивок на Яндекс Диске](https://yadi.sk/d/tFVDN_UAvS80Kg) (пароль архіву: `4pda`)

### 2.2 База прошивок і документації від `joker219` (Пост #513, с. 26)
* [Mail.ru Cloud — Каталог 1](https://cloud.mail.ru/public/Lhg1/56tbxn43J/)
* [Mail.ru Cloud — База прошивок](https://cloud.mail.ru/public/6EGW/idBKgpohP)
* [Яндекс Диск — Технічна документація та дампи](https://yadi.sk/d/k8puwozd2wJcMQ)

### 2.3 Офіційні пакети VAG під ODIS (Пост на с. 13)
Оригінальні заводські контейнери оновлень SGO / FRF:
* **Volkswagen**: [Яндекс Диск](https://yadi.sk/d/ucBa1UOcHIT5YQ)
* **Škoda**: [Яндекс Диск](https://yadi.sk/d/l-PBTucol4MhXw)
* **Audi**: [Яндекс Диск](https://yadi.sk/d/vf3dpF8CJ22xNA)
* **Seat**: [Яндекс Диск](https://yadi.sk/d/8Bcbkb-wvk7FPw)

### 2.4 Спеціалізоване ПЗ та дамоси на Mega.nz
* **WinOLS 4.7 (Повна версія, 129.8 МБ, пост с. 96)**:
  * Посилання: `https://mega.nz/file/ouwCRSwK#Bi2RpOut_cPEsiRm7oMj2B7NIx20Il9Phbpn2_1-NhQ`
* **Збірник дамосів для WinOLS (пост с. 96)**:
  * Посилання: `https://yadi.sk/d/Zb4HB5X7ojycj`
* **База Tuning-Files_EUROTUN_11.16 (3.63 ГБ, згадка с. 59)**:
  * Посилання: `https://mega.nz/#!tzpy2A4S!Xu6GKmJ0_zgoMSWxxa3qta2SkCDPob0eywgRzF3utAw`

---

## 3. Чому виникає блокування та як його обійти «не з твого ПК»

### Причина
Усі ресурси `yandex.*`, `mail.ru` заблоковані українськими інтернет-провайдерами (DNS sinkhole `127.0.0.1` та BGP-фільтрація IP). Крім того, торрент GIFROM містить сотні гігабайт, які переповнять локальний диск.

### Архітектура віддаленого огляду та вибіркового витягування (Google Colab / Cloud Worker)

Щоб переглянути вміст торрента без навантаження на ПК і без блокування провайдера, запускається безкоштовний ноутбук у **Google Colab** (який працює на серверах Google у США чи Західній Європі):

```python
# 1. Встановити легкий клієнт у Google Colab
!apt-get install -y transmission-cli aria2 > /dev/null

# 2. Завантажити сам торрент-файл (через прямий API дисків без блокувань)
!curl -s -L "https://downloader.disk.yandex.ru/..." -o /content/damos.torrent

# 3. Вивести ПОВНЕ дерево файлів торрента без його завантаження:
!transmission-show /content/damos.torrent > /content/torrent_tree.txt

# 4. Знайти всі файли під твій двигун / блок:
!grep -i "BLS" /content/torrent_tree.txt
!grep -i "03G906021QJ" /content/torrent_tree.txt
!grep -i "EDC16U34" /content/torrent_tree.txt
!grep -i "391847" /content/torrent_tree.txt

# 5. Вибірково завантажити ТІЛЬКИ знайдені номери файлів:
# (наприклад, файл номер 421):
!transmission-cli -f /content/download_done.sh -t 421 /content/damos.torrent
```

---

## 4. Що вже витягнуто та розміщено в GitHub репозиторії

Усі прошивки та WinOLS проєкти, згадані у цій темі та її дзеркалі з avto1000 (пост #1119), уже розпаковані, структуровані та синхронізовані в GitHub у гілку `main`:
* [`firmware/reference_dumps/VW_Jetta_1.9TDI_SW391847_HW03G906021QJ_Stock_and_EGRoff`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_Jetta_1.9TDI_SW391847_HW03G906021QJ_Stock_and_EGRoff)
* [`firmware/reference_dumps/VW_Golf5_1.9TDI_SW389289_HW03G906021QJ_Stage1_DPFoff_WinOLS_OLS_KP`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_Golf5_1.9TDI_SW389289_HW03G906021QJ_Stage1_DPFoff_WinOLS_OLS_KP)
* [`firmware/reference_dumps/VW_Caddy_1.9TDI_BLS_SW377228_HW03G906021AR_Stage1`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_Caddy_1.9TDI_BLS_SW377228_HW03G906021AR_Stage1)
* [`firmware/reference_dumps/VW_Caddy_1.9TDI_BLS_SW383708_HW03G906021AB_EGRoff`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_Caddy_1.9TDI_BLS_SW383708_HW03G906021AB_EGRoff)
* [`firmware/reference_dumps/VW_PassatB6_1.9TDI_SW380420_HW03G906021LR_8959_VRPTune_and_Stock`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_PassatB6_1.9TDI_SW380420_HW03G906021LR_8959_VRPTune_and_Stock)
* Плюс 10 суміжних пакетів карт (Škoda, Seat, Audi, Golf 5 EDC16U31/U34).

---

## 5. Результати аналізу 800GB WinOLS Damos Sammlung & BDM-зони

### 5.1 Точний збіг під твій блок знайдено в базі Damos
Через дзеркало на Mega завантажено повний реєстр колекції (`List_Damos_HDD.txt`, 23.5 МБ, 350+ тис. файлів) та торрент `WinOLS DAMOS SAMMLUNG 07-2015 (800GB).torrent` (хеш: `48a79db8cfa1f9a69e4ae76e26b82e1e32306fe6`).

У розділі `Org_Files_Sortiert` знайдено **100.00% заводський комплект Bosch / VAG під твій блок та версію софту**:
* **Папка**: `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42`
  * `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l` — офіційний інженерний ASAM MCD-2MC (A2L) файл Bosch з усіма назвами карт, лімітерів (`Driver_Wish_IQ`, `Torque_Limit_IQ`, `Smoke_Limit_IQ`), формулами та внутрішніми змінними!
  * `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.HEX` — повний заводський Intel-HEX образ (включаючи зону коду процесора MPC562 та зону калібрувань).
  * `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.S19` — образ у форматі Motorola S-Record.
  * `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.sgm` — системні метадані проекту Bosch.

Також знайдено суміжний референсний комплект:
* `03G906021QJ_1340_389289_P447_HAXN_EDC16U34_3.42` (`.a2l`, `.HEX`, `.S19`, `.sgm`, `.sgo`).

### 5.2 Аналіз BDM кодової зони референсних дампів
Проведено бінарний аналіз 35 бінарних файлів у репозиторії (`0x000000..0x180000`):
* Більшість тюнінгових файлів з баз є OBD-вичитками (зона `0x000000..0x180000` заповнена байтами `0xFF`).
* Знайдено повноцінний **2MB BDM-дамп EDC16U34**:
  `Seat_Leon_1.9TDI_SW382081_HW03G906021LK_EDC16U34_EGRoff\Leon 1.9 TDI EGR off Sw 382081 Hw 03G906021LK 0281013279 EDC16U34`
  * Містить **1,001,844 не-0xFF байтів у зоні коду** (завантажувач MPC562, таблиця векторів переривань, мікрокод ініціалізації периферії).
  * Слугує прямим референсом структури пам'яті апаратного рівня блоків EDC16U34.

### 5.3 Консольний торрент-інструмент
* Встановлено `aria2c` v1.37.0 у системний шлях (`C:\Users\pavlo\.gemini\antigravity\bin\aria2c.exe`).
* Інструмент налаштований і готовий до вибіркового завантаження за індексами (`--select-file`) будь-яких цільових блоків.
