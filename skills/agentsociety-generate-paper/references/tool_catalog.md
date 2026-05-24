# paper-toolkit Tool Catalog

Workspace: `paper init`, `paper status`, `paper scan`.

Evidence: `paper evidence add-claim`, `add-evidence`, `add-citation`, `link`, `rm-node`, `rm-edge`, `validate`, `topo-order`, `render-mermaid`.

Templates: `paper template list`, `paper template expand`.

Checks: `paper check style`, `citations`, `figures`, `figure-qa`, `claim-coverage`, `word-count`, `logic-consistency`, `all`.

`paper check figure-qa` opens every `paper/figures/*.pdf`, measures the
`MediaBox` width in millimetres, and inspects each font for an approved
family (Arial / Helvetica / DejaVu / Liberation) plus `FontFile*` embedding.
Warnings: width outside ±10 mm of 89 mm (single) / 183 mm (double), or a
non-standard family. Errors: a referenced font is not embedded.
No LLM, no judgement — just the mechanical check.

Compose and typeset: `paper compose pack-figures`, `write-bib`, `assemble-latex`, `paper compile-once`.

`assemble-latex` writes `paper/main.tex` against the bundled Springer Nature
`sn-jnl` class (option `sn-nature`) and copies `sn-jnl.cls` + `sn-nature.bst`
into `paper/` so `pdflatex`/`bibtex` resolve them locally. The abstract section
file is consumed into the preamble as `\abstract{...}`; all other sections are
`\input`'d in `_SECTION_ORDER`.

Figures: `paper figure render --spec paper/figure_specs/<id>.json`,
`paper figure render-all`, `paper figure list-palettes`. Each render writes
both `paper/figures/<id>.pdf` and a wrapper `paper/figures/<id>.tex` that the
section `\input`s. Spec schema: `references/figure_table_specs.md`.

Tables: `paper table render --spec paper/table_specs/<id>.json`,
`paper table render-all`. Each render writes `paper/tables/<id>.tex` (booktabs);
the section `\input`s it. Spec schema: `references/figure_table_specs.md`.

Literature: `paper lit search --source {arxiv|crossref|openalex} --query "..."`,
`paper lit fetch-doi --doi <doi> --source {crossref|openalex}`,
`paper lit to-bibtex --input <jsonl>`, `paper lit merge-bib --input <jsonl> ...`.
All searches write a JSONL index to `paper/lit/<source>_<slug>.jsonl`; merge
appends new entries to `paper/refs.bib` and dedupes by cite key. Set
`PAPER_TOOLKIT_MAILTO=you@example.org` for polite CrossRef / OpenAlex
identification. The Skill drives query crafting and relevance filtering;
the toolkit owns HTTP, parsing, BibTeX emission, and dedup.

References hygiene: `paper refs dedup` (read-only report) and
`paper refs dedup --apply` (rewrite `refs.bib` dropping absorbed entries).
Match rule: identical normalized DOI, or — for DOI-less entries — identical
first-author surname plus title Jaccard >= 0.90 over tokenized,
stopword-filtered titles. Survivors keep their original `source_text` byte-
for-byte; only absorbed entries are removed.

Page inspection: `paper page count`, `paper page elements`, `paper page overflow`.
