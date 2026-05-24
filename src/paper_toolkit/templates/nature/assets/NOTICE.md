# Vendored Springer Nature LaTeX Template

These files are copied verbatim from the Springer Nature article template
(`sn-article-template`, v3.1 December 2024) and are bundled here so that
`paper-toolkit` can produce a compile-ready Springer Nature manuscript
without requiring the user to install the class and BibTeX style by hand.

- `sn-jnl.cls` — the Springer Nature journal class. Distributed under the
  LaTeX Project Public License (LPPL) v1.3c or later, as stated in the
  file header.
- `sn-nature.bst` — the BibTeX style selected when the class is loaded
  with the `sn-nature` option.

The upstream template (including additional `.bst` variants and a user
manual) is available from Springer Nature. Authors retain full rights to
the content they generate using these files; the files themselves are
redistributed unmodified under the LPPL.

If a newer version of the template is needed, replace the two files with
the latest versions and re-run `paper compose assemble-latex` so the
workspace copy stays in sync.
