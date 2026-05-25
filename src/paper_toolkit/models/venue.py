"""Venue configuration for checkers."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from paper_toolkit.models.check_report import Severity
from paper_toolkit.paths import WorkspacePaths


class SectionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    word_range: tuple[int, int]


class FigureConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caption_words: tuple[int, int] = (25, 200)
    max_figures: int = 6


class StyleRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    reason: str
    severity: Severity = "error"


class StyleRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banned_punct: list[StyleRule] = Field(default_factory=list)
    banned_phrases: list[StyleRule] = Field(default_factory=list)
    preferred_phrases: list[str] = Field(default_factory=list)


class VenueConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    sections: list[SectionRule]
    figure_constraints: FigureConstraints = Field(default_factory=FigureConstraints)
    citation_style: str = "nature"
    templates_dir: str = "nature"
    style_rules: StyleRules = Field(default_factory=StyleRules)
    # `extends:` is accepted for documentation purposes only — paper/venue.yaml is
    # always merged on top of the built-in nature defaults, so the value is unused.
    extends: str | None = None

    @property
    def section_names(self) -> list[str]:
        return [section.name for section in self.sections]

    def word_range_for(self, section_name: str) -> tuple[int, int] | None:
        for section in self.sections:
            if section.name == section_name:
                return section.word_range
        return None


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _builtin_venue_data() -> dict[str, Any]:
    builtin = files("paper_toolkit.venues").joinpath("nature.yaml")
    data = yaml.safe_load(builtin.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def load_venue(*, workspace: Path, venue_name: str) -> VenueConfig:
    paths = WorkspacePaths(workspace=workspace)
    if paths.venue_yaml.exists():
        data = _merge_dict(_builtin_venue_data(), _read_yaml(paths.venue_yaml))
        return VenueConfig.model_validate(data)
    if venue_name != "nature":
        raise ValueError(
            f"unknown venue {venue_name!r}: no paper/venue.yaml found and the only built-in "
            "venue is 'nature'. Create paper/venue.yaml (it will be merged on top of the "
            "built-in nature defaults — list only the keys you want to override)."
        )
    return VenueConfig.model_validate(_builtin_venue_data())
