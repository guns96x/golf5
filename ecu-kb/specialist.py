#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
specialist.py — Вузькопрофільний експерт-спеціаліст з дизельних систем (EDC16U34 / 1.9 TDI BLS)

Головний інваріант: НЕПОХИТНІСТЬ ТА АНТИ-СИКОФАНТІЯ.
Ніяких галюцинацій. Ніяких поступок («ой, ви праві») без першоджерела.
Працює з локальною базою знань (A2L, SQLite FTS5, перевірені claims, першоджерела).
Підтримує роботу як локально (детерміновано), так і з делегуванням до Codex Sol 5.6 чи Claude.
"""

import sys
import os
import re
import json
import sqlite3
import argparse
import subprocess
from pathlib import Path

# Гарантуємо UTF-8 для виводу у Windows консоль
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

KB_DIR = Path(__file__).resolve().parent
DB_PATH = KB_DIR / "knowledge" / "kb.sqlite3"
SCRIPTS_DIR = Path("C:/Users/pavlo/.gemini/config/scripts")


class DieselSpecialist:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Базу знань не знайдено за шляхом: {self.db_path}")
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def get_proven_claims(self, query=None):
        """Отримати всі верифіковані твердження або відфільтровані за запитом."""
        cur = self.conn.cursor()
        if query:
            words = [w.strip() for w in query.split() if len(w.strip()) > 2]
            if not words:
                words = [query.strip()]
            clause = " OR ".join(["statement LIKE ?" for _ in words])
            params = [f"%{w}%" for w in words]
            sql = f"""
                SELECT c.id, c.statement, c.evidence_kind, c.verification_state,
                       c.ecu_variant, c.sw_number, c.engine_code, c.turbo_model,
                       ci.quote, ci.locator, d.rel_path as doc_name
                FROM claims c
                LEFT JOIN citations ci ON ci.claim_id = c.id
                LEFT JOIN documents d ON d.sha256 = ci.doc_sha256
                WHERE ({clause}) AND c.retracted_at IS NULL
            """
            cur.execute(sql, params)
        else:
            sql = """
                SELECT c.id, c.statement, c.evidence_kind, c.verification_state,
                       c.ecu_variant, c.sw_number, c.engine_code, c.turbo_model,
                       ci.quote, ci.locator, d.rel_path as doc_name
                FROM claims c
                LEFT JOIN citations ci ON ci.claim_id = c.id
                LEFT JOIN documents d ON d.sha256 = ci.doc_sha256
                WHERE c.retracted_at IS NULL
            """
            cur.execute(sql)
        return cur.fetchall()

    def search_a2l_symbols(self, query, limit=10):
        """Знайти точні ідентифікатори та карти в A2L."""
        cur = self.conn.cursor()
        # Якщо запит містить кілька слів, шукаємо перше англомовне слово / токен
        tokens = [w for w in re.findall(r'[A-Za-z0-9_]{3,}', query)]
        if not tokens:
            tokens = [query.strip()]
        token = tokens[0]

        cur.execute("""
            SELECT name, obj_type as type, address, func_group, description
            FROM a2l_objects
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY (name LIKE ?) DESC
            LIMIT ?
        """, (f"%{token}%", f"%{token}%", f"{token}%", limit))
        return cur.fetchall()

    def search_literature_chunks(self, query, limit=5):
        """Повнотекстовий пошук у чанках першоджерел (FTS5 або LIKE)."""
        cur = self.conn.cursor()
        # Спершу пробуємо FTS5
        try:
            cur.execute("""
                SELECT ch.id, ch.page_from, ch.page_to, ch.content, d.rel_path, s.obtainability
                FROM chunks_fts f
                JOIN chunks ch ON ch.id = f.rowid
                JOIN documents d ON d.id = ch.document_id
                JOIN sources s ON s.id = d.source_id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            res = cur.fetchall()
            if res:
                return res
        except Exception:
            pass

        # Fallback на LIKE
        cur.execute("""
            SELECT ch.id, ch.page_from, ch.page_to, ch.content, d.rel_path, s.obtainability
            FROM chunks ch
            JOIN documents d ON d.id = ch.document_id
            JOIN sources s ON s.id = d.source_id
            WHERE ch.content LIKE ?
            LIMIT ?
        """, (f"%{query}%", limit))
        return cur.fetchall()

    def evaluate_hypothesis(self, text):
        """
        Детермінована перевірка відомих пасток і хибних суджень.
        Запобігає галюцинаціям та підлабузництву.
        """
        lower = text.lower()
        checks = []

        # 1. Пастка виробника турбіни
        if "garrett" in lower and any(x in lower for x in ["турбін", "turbo", "bls", "bv39"]):
            checks.append({
                "verdict": "CONTRADICTED",
                "topic": "Виробник турбокомпресора",
                "explanation": (
                    "СПРОСТОВАНО: На двигуні 1.9 TDI BLS з фільтром DPF встановлено турбіну "
                    "BorgWarner / KKK BV39A-0072 (OE 03G253014M, BW 54399880072). "
                    "Garrett GT1646V / GT1749V стосується інших кодів (наприклад, BKC/BXE без DPF). "
                    "Твердження про Garrett для BLS є помилковим."
                )
            })

        # 2. Пастка «підняти наддув до 2.5 бар»
        if any(x in lower for x in ["2.4", "2.5", "2.6", "2500", "2400"]) and any(x in lower for x in ["наддув", "тиск", "boost", "mbar", "бар"]):
            checks.append({
                "verdict": "PHYSICAL_RISK",
                "topic": "Безпечний абсолютний тиск наддуву BV39",
                "explanation": (
                    "КРИТИЧНИЙ РИЗИК: Заводська уставка максимального наддуву стоку становить 2050 мбар "
                    "(лімітер за атмосферним тиском PCR_pBDesMaxAP_MAP — до 2350 мбар). "
                    "Турбіна BV39 має малий діаметр вала та чутлива до розгону компресорного колеса (overspeed). "
                    "Встановлення тиску 2400-2500 мбар призводить до перевищення критичної швидкості обертання вала "
                    "та помпажу компресора. Твердження про безпечність 2.5 бар відхилено."
                )
            })

        # 3. Пастка передчасного тюнінгу
        if any(x in lower for x in ["stage 1", "stage 2", "тюнінг", "прошити", "додати палива", "chip tuning"]):
            checks.append({
                "verdict": "PROTOCOL_VIOLATION",
                "topic": "Черговість робіт проєкту",
                "explanation": (
                    "ПОРУШЕННЯ ПРОТОКОЛУ РОБІТ: Згідно з головним правилом проєкту, СПОЧАТКУ будується "
                    "повний верифікований опис заводського стоку та доказова база знань. Модифікація прошивки "
                    "розглядається виключно після повної готовності бази і верифікації першоджерел."
                )
            })

        return checks

    def consult(self, question, engine="local"):
        """
        Головний вхід для консультації:
        1. Збір доказів з локальної БД (A2L + Claims + Chunks).
        2. Детермінований арбітраж на відомі пастки.
        3. Формування непохитної відповіді (або виклик LLM у строгому режимі).
        """
        proven = self.get_proven_claims(question)
        a2l_hits = self.search_a2l_symbols(question, limit=5)
        chunks = self.search_literature_chunks(question, limit=3)
        deterministic_traps = self.evaluate_hypothesis(question)

        # Локальна детермінована генерація звіту
        report = []
        report.append(f"═══════════════════════════════════════════════════════════════════")
        report.append(f"    ВУЗЬКОПРОФІЛЬНИЙ СПЕЦІАЛІСТ EDC16U34 / BLS (Veritas Engine)")
        report.append(f"═══════════════════════════════════════════════════════════════════")
        report.append(f"▶ ЗАПИТ: «{question}»\n")

        if deterministic_traps:
            report.append("── ВЕРДИКТ АРБІТРАЖУ (АНТИ-СИКОФАНТІЯ) ──")
            for trap in deterministic_traps:
                report.append(f"⚠ [{trap['verdict']}] {trap['topic']}:")
                report.append(f"   {trap['explanation']}\n")

        report.append("── ВСТАНОВЛЕНІ ПЕРЕВІРЕНІ ФАКТИ (CLAIMS) ──")
        if proven:
            for c in proven[:5]:
                report.append(f"• [ID #{c['id']}] [{c['evidence_kind']}] {c['statement']}")
                if c['quote']:
                    report.append(f"   Джерело: {c['doc_name']} ({c['locator']})")
                    report.append(f"   Цитата: «{c['quote']}»")
        else:
            report.append("  (Прямих затверджених тверджень для цього запиту ще немає в Claims DB)")

        report.append("\n── РЕЛЕВАНТНІ КАРТИ ТА ЗМІННІ A2L ──")
        if a2l_hits:
            for s in a2l_hits:
                report.append(f"• {s['address']} [{s['type']}] {s['name']}: {s['description']}")
        else:
            report.append("  (Точних збігів у списку карт A2L не знайдено)")

        report.append("\n── ПЕРШОДЖЕРЕЛА ТА ЛІТЕРАТУРА (CHUNKS) ──")
        if chunks:
            for ch in chunks:
                draft_tag = " [ЧЕРНЕТКА — НЕ Є ДОКАЗОМ]" if ch['obtainability'] == 'PROJECT_DRAFT' else ""
                clean_txt = " ".join(ch['content'][:220].split())
                report.append(f"• {ch['rel_path']} (стор. {ch['page_from']}){draft_tag}:")
                report.append(f"   «{clean_txt}…»")
        else:
            report.append("  (Відповідних фрагментів у першоджерелах не знайдено -> Потрібно відкрити GAP)")

        report.append("\n───────────────────────────────────────────────────────────────────")
        report.append("ВИСНОВОК СПЕЦІАЛІСТА:")
        if deterministic_traps:
            report.append("Запит містить спростовані або небезпечні припущення. Діяти виключно за OEM-доказами.")
        elif not proven and not a2l_hits and not chunks:
            report.append("ДОКАЗІВ У ЛОКАЛЬНІЙ БАЗІ ЗНАНЬ НЕДОСТАТНЬО.")
            report.append("Правило системи: Не вигадувати і не погоджуватися наосліп. Необхідно завести GAP у kb.sqlite3.")
        else:
            report.append("Відповідь базується виключно на зафіксованих картах A2L та цитатах OEM-літератури.")
        report.append("───────────────────────────────────────────────────────────────────")

        local_output = "\n".join(report)

        if engine == "local":
            return local_output

        # Якщо обрано делегування до Codex або Claude
        if engine in ("codex", "claude"):
            return self._delegate_llm(question, local_output, engine)

        return local_output

    def _delegate_llm(self, question, ground_truth, engine):
        """Виклик зовнішньої моделі з жорстким анти-сикофантичним промптом."""
        prompt = f"""
[ЕПІСТЕМІЧНИЙ АУДИТ ДИЗЕЛЬНОЇ КАЛІБРОВКИ EDC16U34]:
Запит користувача: "{question}"

ЛОКАЛЬНІ ВСТАНОВЛЕНІ ДОКАЗИ ТА КАРТИ A2L:
{ground_truth}

ПРАВИЛА ДЛЯ ВІДПОВІДІ (МАНДАТОРНО):
1. ЗАБОРОНА СИКОФАНТІЇ: Якщо користувач не правий або пропонує небезпечні зміни, СПРОСТУЙ без вибачень.
2. ЗАБОРОНА ГАЛЮЦИНАЦІЙ: Посилайся лише на надані A2L-карти та цитати.
3. Якщо даних бракує — чітко скажи "Даних недостатньо, потрібен GAP", не вигадуй логіку.
"""
        script_file = SCRIPTS_DIR / ("Invoke-Codex.ps1" if engine == "codex" else "Invoke-Claude.ps1")
        if not script_file.exists():
            return f"Помилка: Скрипт {script_file} не знайдено.\n\n{ground_truth}"

        mode = "audit" if engine == "codex" else "debug"
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script_file),
            "-Mode", mode,
            "-Prompt", prompt
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8")
            return f"{ground_truth}\n\n── ВЕРДИКТ {engine.upper()} ──\n{res.stdout}"
        except Exception as e:
            return f"{ground_truth}\n\n[Помилка виклику {engine}: {e}]"


def main():
    parser = argparse.ArgumentParser(description="Вузькопрофільний спеціаліст EDC16U34 / 1.9 TDI BLS")
    parser.add_argument("query", help="Запитання, гіпотеза або перевірка твердження")
    parser.add_argument("--engine", choices=["local", "codex", "claude"], default="local",
                        help="Двигун обробки: local (детермінований), codex або claude")
    args = parser.parse_args()

    spec = DieselSpecialist()
    result = spec.consult(args.query, engine=args.engine)
    print(result)


if __name__ == "__main__":
    main()
