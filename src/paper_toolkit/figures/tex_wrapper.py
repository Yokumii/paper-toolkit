"""Produce the `paper/figures/<id>.tex` wrapper that sections \\input.

The wrapper file contains a `figure` environment with `\\includegraphics`,
caption, and label. Sections cite the figure by `\\ref{<label>}` and pull
the wrapper in with `\\input{figures/<id>.tex}`.
"""

from __future__ import annotations

from paper_toolkit.compose.latex_assembly import latex_escape


def wrap_figure_tex(
    *,
    figure_id: str,
    caption: str,
    label: str,
    width: str,
    placement: str = "tbp",
) -> str:
    """Return the LaTeX source of a single-figure wrapper.

    `width` must be one of `single` or `double`; selects `\\columnwidth`
    versus `\\textwidth` accordingly.
    """
    if width == "single":
        width_clause = "\\columnwidth"
    elif width == "double":
        width_clause = "\\textwidth"
    else:  # defensive — Pydantic should have caught this upstream.
        raise ValueError(f"unsupported width {width!r}; expected 'single' or 'double'.")
    lines = [
        f"\\begin{{figure}}[{placement}]",
        "  \\centering",
        f"  \\includegraphics[width={width_clause}]{{figures/{figure_id}.pdf}}",
        f"  \\caption{{{latex_escape(caption)}}}",
        f"  \\label{{{label}}}",
        "\\end{figure}",
        "",
    ]
    return "\n".join(lines)
