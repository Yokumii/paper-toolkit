# Literature Search (`paper lit ...`)

Direct public APIs only — no auth, no MCP gateway. The toolkit owns the
HTTP call, the parser, and the BibTeX emission. The Skill owns:

- Query crafting from the research question (multi-query subtopic splits
  if the topic is broad).
- Reading the JSONL index and deciding which entries are actually
  relevant to a claim.
- Composing the `paper evidence add-citation` calls that wire chosen
  entries into the evidence DAG.

## Sources

| Source | Best for | DOI fetch supported |
|---|---|---|
| `arxiv` | Preprints, CS / physics venues, very recent work. | No (use arXiv id). |
| `crossref` | Anything with a DOI — broad coverage of published work. | Yes. |
| `openalex` | Open citation network, abstract reconstruction, author display names. | Yes (DOI URL form). |

Set `PAPER_TOOLKIT_MAILTO=you@example.org` before running so CrossRef
and OpenAlex prioritize the requests.

## Verbs

```
paper lit search --source arxiv     --query "cross-cutting news exposure" --limit 10 --workspace .
paper lit search --source crossref  --query "affective polarization replication" --year-from 2019 --workspace .
paper lit search --source openalex  --query "agent-based replication"             --year-to   2023 --workspace .
paper lit fetch-doi --doi 10.1126/science.aap9559 --source crossref               --workspace .
paper lit fetch-doi --doi 10.1038/s41586-021-04106-w --source openalex            --workspace .
paper lit to-bibtex --input paper/lit/crossref_polarization.jsonl                 --workspace .
paper lit merge-bib --input paper/lit/crossref_polarization.jsonl                 --workspace .
paper lit merge-bib --input paper/lit/a.jsonl --input paper/lit/b.jsonl           --workspace .
```

## Output shapes

Each search produces one JSON object per line at
`paper/lit/<source>_<slug>.jsonl`:

```json
{
  "source": "crossref",
  "source_id": "10.1126/science.aap9559",
  "title": "Sleep deprivation impairs cognition",
  "authors": ["Matthew Walker", "Ada Smith"],
  "year": 2018,
  "venue": "Science",
  "doi": "10.1126/science.aap9559",
  "url": "https://...",
  "abstract": "...",
  "entry_type": "article",
  "cite_key": "walker2018_a53f"
}
```

`cite_key` is `<lastname><year>_<title-hash4>` (deterministic). Use it
as the BibTeX key after `paper lit merge-bib`. `entry_type` is mapped to
BibTeX shapes so `refs.bib` field routing (journal vs booktitle vs
institution vs school) stays correct without re-classification.

## Merge semantics

`paper lit merge-bib` is **append-only**:

- Existing entries in `paper/refs.bib` are preserved verbatim.
- New entries are appended in input order.
- Incoming entries whose cite key already exists are listed under
  `skipped` in the envelope (no overwrite).

Pair with `paper compose write-bib` only when the evidence DAG is the
source of truth for citations (older flow). For the lit-search flow,
prefer `merge-bib` so we never lose hand-curated entries.

## Workflow

1. Write a query that targets a single concrete claim (broad surveys
   waste calls).
2. `paper lit search --source <s> --query "..." --workspace <ws>`.
3. Read `paper/lit/<source>_<slug>.jsonl` (one JSON per line).
4. For each relevant entry, decide a cite key (often the auto-generated
   one is fine) and run `paper evidence add-citation --cite-key ...`.
5. `paper lit merge-bib --input paper/lit/<source>_<slug>.jsonl` so the
   keys actually exist in `refs.bib`.
6. `paper compose write-bib` runs the original evidence-graph-driven
   path (if you also added citation nodes there).
7. `paper check citations` confirms every `\cite{}` resolves.

## When to use which source

- Need a known DOI's metadata: `crossref` first; fall back to `openalex`
  if CrossRef returns a sparse record (some open-access journals are
  better indexed by OpenAlex).
- Looking for a preprint or unpublished work: `arxiv`.
- Need open citation counts or open-access PDF discovery: `openalex`.
- For broad topic surveys: combine — `arxiv` + `crossref` will not
  return identical results, and OpenAlex often catches grey literature
  the other two miss.

## Failure modes

- `LIT_HTTP_ERROR` — upstream non-2xx or network timeout. Inspect the
  envelope's `message`; retry after a few seconds for 5xx; widen the
  query for 0-result responses (which are reported as success with
  `count: 0`).
- `LIT_UNKNOWN_SOURCE` — typo in `--source`. Only `arxiv`, `crossref`,
  `openalex` are accepted.
- `LIT_INPUT_NOT_FOUND` / `LIT_INPUT_INVALID` — `to-bibtex` or
  `merge-bib` cannot read the JSONL; either the file is missing or a
  line is malformed.
