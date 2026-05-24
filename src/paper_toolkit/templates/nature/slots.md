# Nature Template Slot Syntax

Templates in `src/paper_toolkit/templates/nature/sections/*.tex` (or any user
override in `<workspace>/paper/templates/sections/*.tex`) use placeholder
markers that `paper template expand` rewrites into a structured TeX comment +
placeholder snippet. The toolkit never fills slots itself; the Claude Code
operator is expected to read the placeholder and replace it with concrete LaTeX.

## Syntax

```
{{slot:NAME | KEY=VALUE, KEY=VALUE, ...}}
```

- **NAME** is a stable identifier inside the section (e.g. `hook`, `central_claim`).
- After `|`, comma-separated `KEY=VALUE` pairs control rendering. Whitespace is
  insignificant. Values may be bare tokens or `"quoted strings"`.

## Recognised attributes

| Attribute | Type | Meaning |
|---|---|---|
| `kind` | enum: `prose` \| `claim_ref` \| `claim_list` \| `evidence` \| `citation` | What the operator must produce in this slot. `claim_ref` and `claim_list` MUST point to claim ids that exist in the evidence DAG. |
| `words` | range (`MIN-MAX`) or number | Target word count, enforced later by `paper check word-count`. |
| `min`, `max` | integers | Item-count bounds for list-shaped slots (e.g. enumerate contributions). |
| `guidance` | quoted string | Authoring guidance shown to the operator in the rendered placeholder. |
| `requires_evidence` | `true` \| `false` | If true, the operator must back this slot with at least one evidence node before `paper check claim-coverage` will pass. |

Unknown attributes are preserved verbatim in the rendered placeholder so the
operator can read them without the template engine rejecting the slot.

## Examples

```latex
{{slot:hook | kind=prose, words=80-120,
  guidance="Open with a concrete scientific or societal puzzle."}}

We argue that {{slot:central_claim | kind=claim_ref, requires_evidence=true}}.

\begin{enumerate}
{{slot:contributions | kind=claim_list, min=2, max=4}}
\end{enumerate}
```

After `paper template expand --section intro` the placeholder block contains:

- A LaTeX comment with the rendered guidance / constraints (so the operator
  sees them in their editor).
- The original `{{slot:...}}` line preserved as anchor, ready for the operator
  to replace.

## Customising templates

Drop a file at `<workspace>/paper/templates/sections/<section>.tex` to override
a bundled Nature template. The toolkit picks the workspace copy first, then
falls back to the packaged template under `paper_toolkit/templates/nature/`.
