# paper-toolkit

Deterministic Python tooling for the fixed steps of academic-paper development —
workspace setup, evidence-DAG management, structured checks, LaTeX composition,
compile + page introspection, figure rendering, literature search, and an
analysis pipeline that feeds the manuscript.

The toolkit contains **no LLM calls**. All writing, review, and judgment lives
in the companion Claude Code skills, which call into this CLI for everything
that should be reproducible.

## Why

Paper drafts drift between agents, sessions, and editors. The toolkit pins the
mechanical parts — schemas, checks, file layout, LaTeX compose, evidence DAG —
so the agent only owns prose. Two skills ship with the package:

- **`agentsociety-analysis`** — runs the 6-stage analysis pipeline
  (frame → explore → claims → refine → produce → synthesis) against an
  experiment SQLite database, emitting bilingual reports + publication-grade
  figure specs.
- **`agentsociety-generate-paper`** — turns analysis outputs into a
  Springer-Nature-style manuscript: intake, drafting, checks, skeptical review,
  revision loop, and compile.

## Install

Requires Python ≥ 3.11.

```bash
# from a clone (recommended for now)
git clone https://github.com/Yokumii/paper-toolkit.git
cd paper-toolkit
uv sync

# or with pip
pip install .
```

LaTeX (TeX Live / MacTeX) is required for `paper compile-once` and
`paper figure render`. The toolkit shells out to `latexmk` / `bibtex` /
`pdflatex` and parses their logs deterministically.

## Quick start

```bash
# 1. create a workspace
uv run paper init --title "Demo" --venue nature --language en --workspace ./demo

# 2. seed an evidence node + claim
uv run paper evidence add-claim --workspace ./demo \
    --node-id c_warming --label "Mean temperature rose 1.1 K" --strength primary

# 3. render a figure from a JSON spec
uv run paper figure render --spec ./demo/paper/figure_specs/f_trend.json --workspace ./demo

# 4. compose and compile
uv run paper compose pack-figures --workspace ./demo
uv run paper compose write-main --workspace ./demo
uv run paper compile-once --workspace ./demo

# 5. structured checks
uv run paper check style --workspace ./demo
uv run paper check claim-coverage --workspace ./demo
uv run paper check figures --workspace ./demo
uv run paper check figure-qa --workspace ./demo
uv run paper status --workspace ./demo
```

Run `uv run paper <group> --help` for the full verb list in each group, or
see the `dev` branch for the long-form design and plan documents.

## CLI surface

| Group | Purpose |
|---|---|
| `paper init` / `status` / `scan` | Workspace lifecycle and snapshotting |
| `paper evidence` | Evidence DAG: nodes, edges, claim/evidence linking |
| `paper template` | List and expand section templates |
| `paper compose` | Pack figures, write `main.tex`, write `refs.bib` |
| `paper compile-once` / `page` | LaTeX compile + page-metadata inspection |
| `paper check` | `style`, `figures`, `claim-coverage`, `figure-qa` |
| `paper figure` / `table` | Render figures and LaTeX tables from JSON specs |
| `paper lit` | Direct-API search (arXiv / CrossRef / OpenAlex) → `refs.bib` |
| `paper refs` | Inspect and dedup `refs.bib` (DOI + title-Jaccard fallback) |
| `paper analysis` | 6-stage analysis pipeline + lift-to-evidence bridge |

Every command emits a JSON `Envelope` on stdout (success, payload, errors) so
the skills can route on structured results rather than parsing prose.

## Using the Claude Code skills

The skills live under `skills/` and are picked up automatically when
paper-toolkit is installed as a Claude Code plugin.

```jsonc
// in .claude-plugin/marketplace.json
{
  "plugins": [
    {
      "name": "paper-toolkit",
      "source": "https://github.com/Yokumii/paper-toolkit"
    }
  ]
}
```

Inside a Claude Code session:

```
/skill agentsociety-analysis        # run the analysis pipeline
/skill agentsociety-generate-paper  # draft, check, and compile the manuscript
```

Both skills read their `SKILL.md` router first, then dispatch to per-stage
prompts and subagents (`data-explorer`, `claim-extractor`, `figure-reviewer`,
`report-producer`, `skeptical-reviewer`, …). All deterministic steps go through
this CLI; the skills never invent file paths or schemas.

## Repository layout

```
src/paper_toolkit/      # the CLI + library (no LLM calls)
  cli/                  # Typer groups (init, evidence, compose, check, figure, lit, refs, analysis, ...)
  models/               # Pydantic v2 schemas (paper.json, evidence graph, claims, ...)
  analysis/             # 6-stage pipeline: db, state, claims, synthesis, lift
  figures/              # JSON-spec → matplotlib renderer (Arial fallback, pdf.fonttype=42, 89/183mm)
  checkers/             # style, figures, claim-coverage, figure-qa
  refs/                 # bib parser + dedup engine
  lit/                  # arXiv / CrossRef / OpenAlex search
  typeset/              # main.tex composition + LaTeX log parsing
skills/
  agentsociety-analysis/
  agentsociety-generate-paper/
tests/                  # 293 unit + integration tests
```

## Design principles

- **No LLM in the toolkit.** Every CLI verb is pure Python + stdlib + a few
  scientific deps (matplotlib, pypdf, httpx). The agent decides what to write;
  the toolkit decides what's legal.
- **Schemas at every boundary.** Pydantic v2 with `extra="forbid"` on every
  artifact: `paper.json`, evidence graph, claims, figure specs, check reports.
- **Derived state, no phase machines.** State files record facts; stages are
  derived from artifact presence + schema validity, so the agent can't lie
  about progress.
- **Idempotent bridges.** `paper figure register` and
  `paper analysis lift-to-evidence` are safe to re-run — they update existing
  rows in place.

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
```

The full design history and per-phase implementation plans live on the `dev`
branch (`docs/design.md`, `docs/plans/`).

## License

MIT — see `LICENSE`.
