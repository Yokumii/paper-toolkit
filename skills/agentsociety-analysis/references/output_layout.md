# Output layout — what lives where

The `agentsociety-analysis` skill writes to two sibling trees in the
workspace: `analysis/` for analysis-only artifacts; `paper/figure_specs/`
+ `paper/figures/` + `paper/evidence_graph.json` for shared artifacts
the `agentsociety-generate-paper` skill consumes.

```
workspace/
  analysis/
    <hypothesis-id>/
      <experiment-id>/
        state.yaml            # facts only: db_path, profiled_tables, claim_count, last_query_slug
        config.yaml           # language + ids
        analysis_plan.yaml    # research_question + must_inspect + expected_claim_count
        eda/
          <table>_profile.json
          queries/
            <slug>.json
        claims.json
        report_context.md     # built by build-report-context
        evidence_index.json   # built by build-report-context
        report_zh.md          # author this
        report_en.md          # author this
    synthesis/
      <hypothesis-id>/
        synthesis_brief.json  # built by build-synthesis-brief
        synthesis_report_zh.md   # author this (optional v1)
        synthesis_report_en.md
  paper/
    paper.json                # paper-side artifact index; figure register updates this
    evidence_graph.json       # lift-to-evidence updates this
    figure_specs/
      <id>.json               # author this
    figures/
      <id>.pdf                # paper figure render writes this
      <id>.tex                # paper figure render writes this
```

## Whose tree is whose

| Path | Owner | What you can do |
|---|---|---|
| `analysis/<H>/<E>/state.yaml` | toolkit | read only; touch via `paper analysis ...` verbs |
| `analysis/<H>/<E>/analysis_plan.yaml` | toolkit (after `write-plan`) | author it as a payload file, then `write-plan` it in |
| `analysis/<H>/<E>/eda/*` | toolkit | read; never hand-edit |
| `analysis/<H>/<E>/claims.json` | toolkit (after `record-claim`) | read; mutate only via CLI |
| `analysis/<H>/<E>/report_context.md` | toolkit | read; never hand-edit |
| `analysis/<H>/<E>/evidence_index.json` | toolkit | read; never hand-edit |
| `analysis/<H>/<E>/report_<lang>.md` | YOU | author this; the toolkit reads it for `check-release` |
| `paper/figure_specs/<id>.json` | YOU | author this |
| `paper/figures/<id>.pdf` | toolkit (`paper figure render`) | never hand-edit |
| `paper/paper.json` | toolkit (`paper figure register`) | never hand-edit |
| `paper/evidence_graph.json` | toolkit (`paper analysis lift-to-evidence` + the `agentsociety-generate-paper` skill's evidence verbs) | only mutate via CLI |

## Conventions

- `<hypothesis-id>` / `<experiment-id>` — short slugs, e.g. `h1` / `e3`.
  No spaces; the directory name is the id.
- `<table>_profile.json` filename = `<table>` + `_profile.json`. The
  Explore-stage checker discovers profiles by this suffix.
- Query slugs default to a slugified first 60 chars of the SQL. Override
  with `--out` when you want a stable name.
- Figure ids match `[A-Za-z0-9_-]+`. They appear in three places:
  spec filename, PDF filename, paper.json artifact id.
