# `paper analysis` tool catalog

Workspace: `paper init` (in the `agentsociety-generate-paper` skill), then `paper analysis
init --hypothesis-id H --experiment-id E --db PATH [--language LANG]`.
That creates `analysis/<H>/<E>/{state.yaml, config.yaml}` plus the
`eda/` subtree.

## Per-stage CLI verbs

| Stage | Verb | What it does |
|---|---|---|
| Frame | `paper analysis init` | mkdir experiment tree; write `state.yaml` + `config.yaml`. |
| Frame | `paper analysis write-plan --payload PATH` | save a JSON or YAML plan into `analysis_plan.yaml` (Pydantic-validated). |
| Frame | `paper analysis check-plan` | gate: plan file exists, parses, ids match. |
| Explore | `paper analysis list-tables --db PATH` | enumerate tables + row counts + columns (no workspace required). |
| Explore | `paper analysis profile-table --db PATH --table NAME --hypothesis-id H --experiment-id E` | per-column stats; auto-detects JSON-blob TEXT columns; writes `eda/<table>_profile.json`. |
| Explore | `paper analysis query --db PATH --sql "..." --hypothesis-id H --experiment-id E` | SQL passthrough; refuses `SELECT *` unless `--allow-select-all`; writes `eda/queries/<slug>.json` when bound to an experiment. |
| Explore | `paper analysis check-explore` | gate: every `must_inspect` table from the plan has a profile under `eda/`. |
| Claims | `paper analysis record-claim --claim-id ... --text ... --kind ... --evidence ...` | upserts into `claims.json` (`kind` must be `quantitative \| qualitative \| comparative`). |
| Claims | `paper analysis check-claims` | gate: schema, non-empty, no duplicate ids. |
| Refine | (out-of-band) `paper figure render --spec paper/figure_specs/<id>.json` | renders a PDF + LaTeX wrapper into `paper/figures/`. |
| Refine | (out-of-band) `paper figure register --spec paper/figure_specs/<id>.json` | registers the figure in `paper.json:artifacts.figures[]` (idempotent). |
| Refine | `paper analysis record-figure-contract --claim-id ... --figure-id ... --rationale ...` | binds a claim to its figure spec inside `claims.json`. |
| Refine | `paper analysis check-refine` | gate: every claim has a contract; matching spec + PDF exist. |
| Produce | `paper analysis build-report-context` | emits `report_context.md` + `evidence_index.json` for the report-producer subagent. |
| Produce | (author) `report_zh.md`, `report_en.md` | bilingual reports under `analysis/<H>/<E>/`. |
| Produce | `paper analysis check-release` | gate: report files exist per workspace language. |
| Synthesis | `paper analysis build-synthesis-brief --experiment-id E1 --experiment-id E2 ...` | aggregates claims across experiments into `analysis/synthesis/<H>/synthesis_brief.json`. |
| Synthesis | `paper analysis lift-to-evidence` | promotes claims into `paper/evidence_graph.json` (adds claim + evidence nodes + `supports` edges); idempotent. |
| Synthesis | `paper analysis check-synthesis` | gate: brief exists, claims either lifted or explicitly deferred. |
| Any | `paper analysis status [--hypothesis-id H]` | lists every experiment with its derived stage. |

Every verb routes through `safe_dispatch` and prints exactly one
`Envelope` JSON document to stdout. Exit code 1 iff `errors` is non-empty.

## Two bridge verbs that close the analysis→paper handoff

- `paper figure register --spec PATH` — analysis writes the spec; this
  verb inserts/updates the corresponding `FigureArtifact` so
  `paper compose pack-figures` and `paper check figures` see it.
- `paper analysis lift-to-evidence` — walks `claims.json` and writes the
  claim + evidence nodes + `supports` edges into `paper/evidence_graph.json`.
  Without this step, `paper check claim-coverage` treats analysis claims
  as orphans.

Both verbs are idempotent — re-running them only touches rows that
changed.
