#!/usr/bin/env python3
"""
local-enrich — контекстні префікси до чанків силами локальної моделі.

Навіщо: зараз префікс шаблонний («Уривок з «X», стор. N»). Справжній contextual
retrieval — це одне речення про те, ЧИМ є цей уривок у контексті документа.
Anthropic заміряла на цьому −35% помилок пошуку, і воно покращує лексичний
пошук теж, без жодних векторів.

Працює з будь-яким OpenAI-сумісним ендпоінтом: Ollama, LM Studio, llama.cpp.
Залежностей немає — лише стандартна бібліотека.

    python local_enrich.py --check                    перевірити зв'язок з моделлю
    python local_enrich.py --limit 20 --dry-run       подивитись, що вийде
    python local_enrich.py --limit 200                обробити перші 200
    python local_enrich.py                            усі, що лишились

Перервати можна будь-коли: скрипт продовжить з місця зупинки.
"""
import argparse, json, sqlite3, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB   = ROOT / "knowledge" / "kb.sqlite3"

DEFAULT_URL   = "http://localhost:11434/v1/chat/completions"   # Ollama
DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"

SYSTEM = (
    "Ти складаєш короткі контекстні підписи до уривків технічної документації "
    "про дизельні двигуни та ECU. Твоє завдання — ОПИСАТИ, чим є уривок у "
    "контексті документа, а не переказати його зміст і не додати нічого свого.\n"
    "Одне речення, до 25 слів, мовою уривка. Без вступів на кшталт «Цей уривок». "
    "Якщо уривок — таблиця чи перелік параметрів, так і напиши.\n"
    "НЕ додавай фактів, яких немає в уривку. НЕ роби висновків."
)

PROMPT = """Документ: {title}
Видавець: {publisher}
Розділ бібліотеки: {folder}
Сторінка: {page}

Уривок:
---
{body}
---

Контекстний підпис одним реченням:"""


def connect():
    if not DB.exists():
        sys.exit(f"Бази немає: {DB}")
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    cols = {r[1] for r in c.execute("PRAGMA table_info(chunks)")}
    if "context_source" not in cols:
        c.execute("ALTER TABLE chunks ADD COLUMN context_source TEXT")
        c.commit()
        print("Додано колонку chunks.context_source")
    return c


def call_model(url, model, body, timeout=120):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": body}],
        "temperature": 0.1,      # підпис має бути відтворюваним, не творчим
        "max_tokens": 80,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()


def reindex_chunk(c, chunk_id, content, prefix, section):
    """
    chunks_fts — зовнішня таблиця з тригерами лише на INSERT і DELETE.
    Тому оновлення рядка треба проводити вручну, інакше індекс лишиться
    зі старим текстом і пошук мовчки шукатиме не те.
    """
    c.execute("INSERT INTO chunks_fts(chunks_fts, rowid, content, context_prefix, section)"
              " VALUES('delete', ?, ?, ?, ?)",
              (chunk_id, content, prefix, section))
    c.execute("INSERT INTO chunks_fts(rowid, content, context_prefix, section)"
              " VALUES(?,?,?,?)", (chunk_id, content, prefix, section))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0, help="0 = усі, що лишились")
    ap.add_argument("--dry-run", action="store_true", help="показати, нічого не писати")
    ap.add_argument("--check", action="store_true", help="перевірити зв'язок і вийти")
    ap.add_argument("--include-drafts", action="store_true",
                    help="обробляти й власні чернетки (за замовчуванням — ні)")
    a = ap.parse_args()

    if a.check:
        try:
            out = call_model(a.url, a.model, "Документ: тест\n\nУривок:\n---\nabc\n---\n\nПідпис:", 60)
            print(f"✓ модель відповідає: {out[:80]}")
            return 0
        except Exception as e:
            print(f"✗ немає зв'язку з {a.url}\n  {type(e).__name__}: {str(e)[:120]}")
            print("\n  Ollama:    ollama serve  і  ollama pull qwen2.5:7b-instruct-q4_K_M")
            print("  LM Studio: увімкни локальний сервер, --url http://localhost:1234/v1/chat/completions")
            return 1

    c = connect()
    where = "" if a.include_drafts else "AND s.obtainability != 'PROJECT_DRAFT'"
    q = f"""SELECT ch.id, ch.content, ch.section, ch.page_from,
                   s.title, s.publisher, d.rel_path
            FROM chunks ch
            JOIN documents d ON d.id = ch.document_id
            JOIN sources   s ON s.id = d.source_id
            WHERE (ch.context_source IS NULL OR ch.context_source = '') {where}
            ORDER BY ch.id"""
    rows = c.execute(q).fetchall()
    if a.limit:
        rows = rows[:a.limit]
    if not rows:
        print("Усе вже оброблено.")
        return 0

    total_left = c.execute(
        f"""SELECT COUNT(*) FROM chunks ch
            JOIN documents d ON d.id=ch.document_id JOIN sources s ON s.id=d.source_id
            WHERE (ch.context_source IS NULL OR ch.context_source='') {where}""").fetchone()[0]
    print(f"До обробки: {len(rows)} з {total_left} · модель {a.model}\n")

    t0, done, failed = time.time(), 0, 0
    for r in rows:
        body = PROMPT.format(
            title=str(r["title"])[:90], publisher=str(r["publisher"] or "—")[:50],
            folder=str(r["rel_path"]).split("/")[0], page=r["page_from"] or "—",
            body=r["content"][:2400])
        try:
            prefix = call_model(a.url, a.model, body)
        except Exception as e:
            failed += 1
            print(f"  ✗ #{r['id']}: {type(e).__name__}")
            if failed > 5:
                print("\nЗабагато помилок поспіль — зупиняюсь. Перевір --check.")
                break
            continue
        prefix = " ".join(prefix.split())[:400]

        if a.dry_run:
            print(f"  #{r['id']} стор.{r['page_from']} │ {prefix[:100]}")
        else:
            c.execute("UPDATE chunks SET context_prefix=?, context_source=? WHERE id=?",
                      (prefix, a.model, r["id"]))
            reindex_chunk(c, r["id"], r["content"], prefix, r["section"])
            done += 1
            if done % 25 == 0:
                c.commit()
                rate = done / (time.time() - t0)
                left = (total_left - done) / rate if rate else 0
                print(f"  … {done}  ({rate:.1f}/с, лишилось ~{left/60:.0f} хв)")

    if not a.dry_run:
        c.commit()
        print(f"\nОброблено: {done}   помилок: {failed}")
        print("Далі:  python bench_retrieval.py --compare")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПерервано — прогрес збережено, запусти знову щоб продовжити.")
        sys.exit(130)
