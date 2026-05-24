"""Color palettes for paper-toolkit figures.

Four publication-grade palettes (`nmi_pastel`, `nature_imaging`,
`nature_material`, `nature_clinical`). Each is an ordered list so chart
code can cycle through colors without having to know the named-key layout.
"""

from __future__ import annotations

from typing import Final

# Each palette is an ordered list. Charts cycle through this list when they
# need more than one color (grouped bars, multi-series line, etc.).
PALETTES: Final[dict[str, list[str]]] = {
    "nmi_pastel": [
        "#484878",  # baseline_dark
        "#7884B4",  # baseline_mid
        "#B4C0E4",  # baseline_soft
        "#E4E4F0",  # ours_tiny
        "#E4CCD8",  # ours_base
        "#F0C0CC",  # ours_large
    ],
    "nature_imaging": [
        "#22D7E6",  # cyan
        "#FF2AD4",  # magenta
        "#B8B8B8",  # context
        "#FFFFFF",  # white
    ],
    "nature_material": [
        "#33B5A5",  # teal
        "#77D7D1",  # aqua
        "#7C6CCF",  # violet
        "#B9A7E8",  # lilac
        "#E53935",  # callout_red
        "#D9D9D9",  # neutral
    ],
    "nature_clinical": [
        "#272727",  # baseline
        "#E28E2C",  # week6
        "#D24B40",  # week13
        "#5B8FD6",  # week26
        "#7BAA5B",  # year1
        "#C45AD6",  # year2
    ],
}


def list_palette_names() -> list[str]:
    """Return the sorted list of registered palette names."""
    return sorted(PALETTES.keys())


def resolve_palette(name: str) -> list[str]:
    """Return the color list for `name`. Raises `KeyError` on unknown name."""
    if name not in PALETTES:
        raise KeyError(f"unknown palette {name!r}; pick one of {list_palette_names()}")
    return list(PALETTES[name])
