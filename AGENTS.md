# Global Developer Guidelines & Autonomous Codex Protocol

## 1. Role Division & Primary AI Architecture
- **Primary Driver (Antigravity / Gemini)**:
  - Performs all repository exploration, file searches (`find_by_name`, `grep_search`), project scaffolding, writing code, executing terminal commands, running tests, and routine refactoring.
  - Keeps Codex token consumption low by shielding Codex from routine context scanning and boilerplate operations.
- **Deep Reasoning, Architecture & Auditor (OpenAI Codex CLI - gpt-5.6-sol high)**:
  - Serves as the authoritative deep-thinking engine consulted autonomously before starting projects and whenever encountering problems or bugs.
  - **Preferred Model Policy**:
    - **Primary Deep Reasoning, Pre-Project Planning & Debugging**: Use `gpt-5.6-sol` with `model_reasoning_effort = "high"`.
    - **Code Review**: Use `gpt-5.6-terra` with `model_reasoning_effort = "low"`.
    - **GPT-6 Astra**: Use sparingly, strictly short-lived, with ultra-concise prompts only when exceptional reasoning is required.

---

## 2. Autonomous Codex Delegation Triggers (MANDATORY & ZERO REMINDERS)
The agent MUST automatically invoke the Codex helper script (`C:\Users\pavlo\.gemini\config\scripts\Invoke-Codex.ps1`) under the following conditions without waiting for the user to prompt or remind:

### Trigger 0: Mandatory Consultation Before Starting Any Project / Major Feature
- **When**: BEFORE writing code for any new project, new module, or substantial feature.
- **Action**: Run:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Codex.ps1" -Mode plan -Prompt "<Pre-Project Planning Prompt>"`
- **Prompt Structure**:
  ```markdown
  [СТАРТ ПРОЄКТУ / ПЛАНУВАННЯ]:
  - Мета: <опис мети та вимог>
  - Стек та інструменти: <технології, бібліотеки>
  - Пропонована архітектура: <як я планую розбити модулі, файли, структури даних>
  - Запит до Sol 5.6: Оціни архітектурні ризики, потенційні підводні камені та дай рекомендації перед початком реалізації.
  ```
- **Follow-up**: Incorporate `gpt-5.6-sol`'s recommendations into the implementation plan before generating files.

### Trigger B: Stuck / Problem Escalation (When Something Fails or Doesn't Work)
- **When**: Whenever something does not work (test failure, build error, unexpected runtime behavior, or bug fix fails). Do NOT loop or keep guessing in chat.
- **Action**: Run:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Codex.ps1" -Mode debug -Prompt "<Structured Problem Context>"`
- **MANDATORY Prompt Structure (Strictly follow this format)**:
  ```markdown
  [ОПИС ПРОБЛЕМИ]: <конкретний текст помилки, стектрейс або неочікувана поведінка>
  [ЯК Я ЗБИРАЮСЯ ЦЕ РЕАЛІЗУВАТИ]: <як саме я планую це вирішити або що намагався зробити>
  [ЩО САМЕ НЕ ВИХОДИТЬ]: <де конкретно затик, чому поточний підхід не спрацював>
  [КОНТЕКСТ КОДУ]: <мінімальний релевантний фрагмент коду та файлів>
  ```
- **Follow-up**: Adopt `gpt-5.6-sol`'s diagnosis and implement the verified solution.

### Trigger A: Verification of Non-Trivial Changes (Code Review)
- **When**: After implementing a complex feature, non-trivial logic change, or substantial refactoring, before declaring the task complete.
- **Action**: Run:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Codex.ps1" -Mode review -WorkDir (Get-Location).Path`
- **Default Config**: Model `gpt-5.6-terra`, `effort=low`.
- **Follow-up**: Read Codex findings. If any critical bugs or edge cases were caught, fix them immediately. Inform the user that the code was reviewed and verified with Codex.

### Trigger C: High-Stakes Concurrency & Deadlocks
- **When**: Writing or debugging complex async state machines, multi-threaded mutex/locking, worker thread synchronization, or distributed consensus.
- **Action**:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Codex.ps1" -Mode debug -Model "gpt-5.6-sol" -Effort "high" -Prompt "<Concurrency Scenario & Invariants>"`

### Trigger D: Security & Authentication Audit
- **When**: Touching authentication tokens (JWT, OAuth), role-based access control (RBAC), custom SQL queries, or sensitive data sanitization.
- **Action**:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Codex.ps1" -Mode audit -Prompt "<Security-Sensitive Code & Threat Model>"`
- **Default Config**: Model `gpt-5.6-sol`, `effort=high`.

---

## 3. Autonomous Claude Code Delegation Protocol
Claude Code CLI (`Invoke-Claude.ps1`) is delegated to for high-level software architecture, deep refactorings, and nuanced semantic debugging.

### Trigger E: Architectural Planning & Module Seams
- **When**: Designing new large modules, planning substantial refactorings, or organizing domain boundaries.
- **Action**:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Claude.ps1" -Mode architect -Prompt "<Architecture Request & Invariants>"`
- **Default Config**: Model `claude-3-7-sonnet`, `effort=high`.

### Trigger F: Nuanced Semantic Debugging & UI Logic
- **When**: Complex state/UI synchronization bugs, tricky typing patterns (TypeScript/React/Compose), or when a third authoritative perspective is needed.
- **Action**:
  `powershell -File "C:\Users\pavlo\.gemini\config\scripts\Invoke-Claude.ps1" -Mode debug -Prompt "<Semantic Bug Context & Expected Invariants>"`
- **Default Config**: Model `claude-3-7-sonnet`, `effort=high`.

---

## 4. Research / Project Knowledge Policy

Before answering or making technical decisions, determine whether the task depends on information outside the current prompt.

USE the research skill (`project-research`) when ANY of these are true:
1. The answer depends on facts, decisions, files or research previously collected for this project.
2. The user refers to something discussed or established earlier.
3. Current or external information may materially change the answer.
4. You are uncertain about a technical fact that can be verified.
5. The task requires comparing documentation, specifications, sources, implementations or previous findings.
6. A decision may conflict with previous project decisions.

### When research is needed:

- **STEP 1 — PROJECT KNOWLEDGE FIRST**: Search the local project knowledge base before using the web:
  `python "C:\Users\pavlo\.codex\skills\research\research.py" "<query>" --project <project_name>`
- **STEP 2 — USE EXISTING KNOWLEDGE**: If sufficient reliable information already exists, use it. Do not repeat web research unnecessarily.
- **STEP 3 — WEB ONLY IF NEEDED**: If information is missing, stale, contradictory or insufficient, the tool automatically performs web research/scraping and stores findings under the project namespace (or force with `--force`).
- **STEP 4 — MINIMAL CONTEXT**: Retrieve only the most relevant fragments (the tool outputs compact BM25-ranked snippets). Never inject entire knowledge bases or giant web pages into context.
- **STEP 5 — WRITE BACK**: If new information materially improves the project's understanding, store the useful finding, source URL and date in the project knowledge base (e.g. update `projects/<name>/project_summary.md` and index via `python "C:\Users\pavlo\.codex\skills\research\research.py" index <path> --project <name>`).

### DO NOT use research for:
- Simple code edits where all required information is already in the repository.
- Formatting/refactoring that requires no external knowledge.
- Straightforward calculations.
- Questions completely answered by the current prompt/context.
- Repeated research when valid results already exist locally.

### Priority Hierarchy:
Current task → Project files/context → Project knowledge base → Cached research → Fresh web research

*Never invent missing project facts. If project knowledge and current evidence disagree, prefer the newer verified evidence and record the discrepancy.*

---

## 5. Automatic GitHub Sync Policy
- **Universal Rule**: Every active project MUST be initialized, tracked, and automatically synced with GitHub under the user's account (`guns96x`).
- **Autonomous Push**: After any meaningful feature, bug fix, or refactoring (and before reporting completion to the user), the agent MUST commit and push to the remote branch (`git push origin <branch>`).
- **External AI Accessibility**: Keep public or accessible as requested so that external LLM tools (ChatGPT, Claude web, etc.) can inspect the live codebase at any time via web links.



---

## 6. Remote Knowledge Snapshot Policy (MANDATORY)

The local SQLite database remains canonical, but external AI clients cannot read it directly.
After ANY mutation that changes claims, citations, gaps, conflicts, source metadata or A2L
state, refresh the GitHub-readable specialist snapshot before the final push:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Publish-KBRemoteSnapshot.ps1
```

This command runs `kb.py check`, exports the read-only snapshot with
`ecu-kb/remote_bridge.py`, verifies SHA-256 hashes and stages `ecu-kb/remote/`.

Rules:
- Never hand-edit `ecu-kb/remote/*.json` or `ecu-kb/remote/a2l/*.json`.
- The remote snapshot exporter must never copy `ecu-kb/knowledge/kb.sqlite3`, firmware binaries, or raw corpus contents into `ecu-kb/remote/`. Repository-level source/library publication follows the project's current repository policy separately.
- A Git push that changes KB state without refreshing the remote snapshot is incomplete.
- External AI clients must treat `ecu-kb/remote/manifest.json` as the first entrypoint and
  must not prefer hard-coded prose in prompts or old reports over the current exported DB state.
