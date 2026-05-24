# CLAUDE.md

Instructions for Claude Code (or any agentic worker) sessions opened in this repo.

## Project Identity

This is **paper-toolkit**: a standalone Python package providing deterministic
CLI tools for academic-paper development (workspace state, evidence DAG, checkers,
LaTeX compose, compile + page introspection). It contains **NO LLM calls**.

It was extracted from `agentsociety-v2`'s in-tree paper system. All writing,
review, and revision judgment is done by the Claude Code operator that calls
this CLI — never by the toolkit itself.

## Where to start

1. Read `docs/design.md` (the full spec).
2. Read `docs/plans/` (implementation plans, executed in order: `01-foundation.md`,
   then `02-...`, etc.).
3. Use the `superpowers:executing-plans` or `superpowers:subagent-driven-development`
   skill to work through the next unchecked plan.

**Bootstrap status (read before starting work):** Tasks 1–4 of `01-foundation.md`
were completed in a separate bootstrap session (the one that created this repo).
Resume from **Task 5 (`paths.py`)** in `docs/plans/01-foundation.md`. The git log
already shows commits for Tasks 1–4; do NOT re-run them. The unchecked boxes for
Tasks 1–4 in the plan file are kept as historical record; verify them mentally
against `git log --oneline` before checking them off and moving on.

## Tech stack

- Python **3.11+**
- Dep manager: **uv** — run `uv sync --extra dev` to install dev deps
- CLI: **Typer** — entry point `paper = paper_toolkit.cli.main:app`
- Schema: **Pydantic v2**
- Test: **pytest**, Lint: **ruff**, Type: **mypy** (strict)

## Commands

```bash
uv sync --extra dev                              # install
uv run paper --help                              # CLI smoke test
uv run pytest                                    # all tests
uv run pytest tests/unit/test_envelope.py -v     # single test file
uv run ruff check src tests                      # lint
uv run ruff format src tests                     # format
uv run mypy src                                  # type-check
```

## Conventions

- TDD: write the failing test first, run it, then minimal implementation,
  re-run, commit. Plans give you the exact code; follow them.
- Commit after every passing task (granularity: per Task in the plan).
- All tool subcommands return the JSON `Envelope` defined in `envelope.py`.
- Do NOT add features beyond the current plan's scope. Stub fields that future
  plans will populate (e.g., `claim_count` returns 0 until Plan 2).

## Plans roadmap (informational)

- **Plan 1 (this repo's foundation)** — repo scaffold + `PaperState` + `paper init` / `paper status`.
- **Plan 2** — scanner + evidence DAG (`paper scan`, `paper evidence *`).
- **Plan 3** — compose + typeset (`paper compose *`, `paper compile-once`).
- **Plan 4** — checkers (six `paper check *` subcommands + `paper check all`).
- **Plan 5** — templates + `skills/paper/` + migration of agentsociety-v2.

## Out of scope

This repo is NOT a paper-management system; it does not do literature search,
co-authoring, or submission packaging. See `docs/design.md` §17.
