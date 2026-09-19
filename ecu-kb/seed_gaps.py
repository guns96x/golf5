#!/usr/bin/env python3
"""Початкові прогалини, знайдені під час аудиту корпусу. Запустити раз після init."""
import sqlite3
from pathlib import Path

GAPS = [
 ("Підтвердити BV39 фотом таблички на машині",
  "Зв'язок 03G253014M -> BV39 зроблено за каталогом BorgWarner. Це INFERRED, не MEASURED. "
  "Без підтвердження не можна застосовувати компресорні карти конкретного виконання.", 1,
  "USER_DATA: фото парт-номера турбіни крупним планом"),
 ("Отримати незайманий заводський readback ECU",
  "diagnostic-review/reference-from-hex.analysis-only.bin реконструйований з HEX, "
  "а не знятий з машини. Baseline, з яким порівнюємо зміни, сам не є первинним.", 1,
  "USER_DATA: повний дамп до будь-яких змін, із зазначенням чим і коли знято"),
 ("Знайти точне джерело по Pumpe-Duse",
  "У секції injection лежать VE (VP37), CP1 (Common Rail) і PE/PF (рядні) — жодна "
  "не є системою цієї машини. Bosch UIS/UPS Technical Instruction безкоштовно не знайдено.", 1,
  "WANT_USER_COPY: Bosch Technical Instruction Unit Injector System / Unit Pump System"),
 ("Чи досяжні уставки наддуву режиму регенерації DPF",
  "У прошивці є PCR_facCtlRgn1/2/3 і PCR_facDesRgn1/2/3 — окремі уставки для регенерації. "
  "DPF фізично видалений. Чи ці гілки ще виконуються і як впливають на поведінку — не з'ясовано.", 1,
  "аналіз коду/логіки + телеметрія"),
 ("Скласти словник каналів VCDS (групи 001-125)",
  "Канали приходять як 'Group 011 field 3' з різними одиницями і рейтами. "
  "Без словника логи не крос-запитуються між собою.", 2,
  "USER_DATA: дамп вимірювальних груп на прогрітому холостому ходу"),
 ("Розділити в SSP 304 те, що стосується BLS, і те, що ні",
  "SSP 304 описує керування наддувом через позиційні моторчики V280/V281 по CAN, "
  "а N75 підписаний '(R5-TDI-engine)'. Це Touareg R5/V10. BLS має вакуумний N75 без CAN. "
  "Найавторитетніший EDC16-документ описує іншу реалізацію.", 1,
  "порозділова розмітка застосовності всередині документа"),
 ("Heywood: знайти версію з текстовим шаром",
  "Наявний скан на 481 сторінку має 0 символів тексту і не інгеститься. "
  "Лекції MIT 2.61 частково закривають ту саму тему і вже в корпусі.", 3,
  "WANT_USER_COPY або покластися на MIT 2.61"),
 ("Перевірити походження ISO 14229 і ISO 14230 у корпусі",
  "Обидва стандарти платні. У реєстрі позначені як здобуті. Якщо взяті з неофіційних "
  "дзеркал — тримати лише локально, у git не класти.", 2,
  "звірка license_status у реєстрі"),
]

def main():
    db = Path(__file__).parent / "knowledge" / "kb.sqlite3"
    if not db.exists():
        print("Спершу: python kb.py init"); return
    c = sqlite3.connect(db)
    n = 0
    for q, why, pri, need in GAPS:
        if not c.execute("SELECT 1 FROM gaps WHERE question=?", (q,)).fetchone():
            c.execute("""INSERT INTO gaps(question,why_needed,priority,needed_source)
                         VALUES(?,?,?,?)""", (q, why, pri, need))
            n += 1
    c.commit()
    print(f"Додано прогалин: {n}   (усього відкритих: "
          f"{c.execute(chr(83)+'ELECT COUNT(*) FROM gaps WHERE status=' + chr(39) + 'OPEN' + chr(39)).fetchone()[0]})")

if __name__ == "__main__":
    main()
