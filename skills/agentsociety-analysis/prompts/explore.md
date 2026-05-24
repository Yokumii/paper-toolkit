# Stage 2 — Explore

You are profiling tables and running ad-hoc queries to give the next
stage (Claims) something concrete to point at. The artifacts you write
here become the `evidence` fields in `claims.json`.

## Pre-reads (required)

- `prompts/_writing_shared.md`
- `references/output_layout.md` — eda/ subdirectory shape.
- `references/workflow.md` — `check-explore` gate definition.

## What to do

1. `paper analysis profile-table --db PATH --table NAME --hypothesis-id
   H --experiment-id E --workspace .` for each table in the plan's
   `must_inspect`. The toolkit auto-detects JSON-blob TEXT columns; the
   `eda/<table>_profile.json` artifact is the per-column digest.

2. For each profile, *read it* (Read tool) and write a one-paragraph
   summary into a running notes buffer. Note:
   - Columns that look distributionally unusual.
   - Columns whose distinct-count is suspiciously low (categorical?)
     or suspiciously high (free-text?).
   - JSON columns whose top-level keys hint at sub-structure worth
     further query.

3. Issue targeted queries via `paper analysis query --sql "..."
   --hypothesis-id H --experiment-id E --workspace .`. Each query
   either:
   - Confirms or refutes a hypothesis arising from the research
     question.
   - Builds toward a specific candidate claim (typically a stat like
     mean per arm, count per category, trend over tick).

   Save with `--out` when you want a stable slug. Default slugification
   uses the first 60 chars of the SQL.

4. STOP exploring when the plan's `research_question` has a candidate
   answer (or a clean "no, the data does not support that"). Don't
   fish.

5. `paper analysis check-explore --hypothesis-id H --experiment-id E`.
   Loop until clean.

## Quality bar

- Every column referenced in your running notes is one whose profile
  you actually read.
- Every query slug under `eda/queries/` will be referenced by at least
  one claim.
- The `must_inspect` list is wholly covered.

## Anti-patterns

- Querying for confirmation only. Run at least one query that *could*
  have falsified the working hypothesis.
- Running `SELECT *`. The toolkit refuses without `--allow-select-all`
  for a reason: the payload is too big to reason about.
- Dumping every column's distribution into your context. Use the
  profile artifact; don't paraphrase it back into the conversation.

## Done when

`paper analysis check-explore` is clean AND you have a notes buffer
that says, for the plan's research question, what the candidate answers
are and which slug supports each.
