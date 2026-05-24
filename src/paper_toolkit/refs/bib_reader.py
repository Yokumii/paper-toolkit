"""Minimal BibTeX reader — extracts just the fields we need for dedup.

Full BibTeX is messy (nested braces, balanced groups, @string macros, comment
fields). We need only `cite_key`, `entry_type`, `doi`, `title`, `author`,
`year`. A line-oriented scanner that walks balanced braces is enough; we
never try to *write* via this reader (that path is `lit/bibtex_emit.py`),
so a partial parser cannot corrupt the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ENTRY_HEADER_RE = re.compile(r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,\s]+)\s*,")
_FIELD_RE = re.compile(r"(?P<name>\w+)\s*=\s*", re.IGNORECASE)


@dataclass(frozen=True)
class BibEntry:
    cite_key: str
    entry_type: str
    fields: dict[str, str]
    source_text: str  # raw entry block, including header and closing brace

    @property
    def doi(self) -> str | None:
        return self.fields.get("doi")

    @property
    def title(self) -> str | None:
        return self.fields.get("title")

    @property
    def author(self) -> str | None:
        return self.fields.get("author")

    @property
    def year(self) -> str | None:
        return self.fields.get("year")


def _read_braced_value(text: str, start: int) -> tuple[str, int]:
    """Starting at `text[start]` (must be `{`), return the contents inside the
    balanced braces and the index *after* the closing brace.
    """
    assert text[start] == "{"
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    raise ValueError("unterminated brace group while parsing BibTeX value")


def _read_quoted_value(text: str, start: int) -> tuple[str, int]:
    assert text[start] == '"'
    i = start + 1
    while i < len(text):
        if text[i] == '"' and text[i - 1] != "\\":
            return text[start + 1 : i], i + 1
        i += 1
    raise ValueError("unterminated quoted BibTeX value")


def _read_value(text: str, start: int) -> tuple[str, int]:
    """Parse a BibTeX field value starting at index `start`.

    Returns (value, index-after-value). Skips leading whitespace.
    """
    j = start
    while j < len(text) and text[j].isspace():
        j += 1
    if j >= len(text):
        return "", j
    ch = text[j]
    if ch == "{":
        return _read_braced_value(text, j)
    if ch == '"':
        return _read_quoted_value(text, j)
    # Bare numeric / macro identifier: read until `,` or `}`.
    k = j
    while k < len(text) and text[k] not in ",}\n":
        k += 1
    return text[j:k].strip(), k


def _parse_fields(body: str) -> dict[str, str]:
    """Parse `field = value, field = value` body of a BibTeX entry."""
    fields: dict[str, str] = {}
    i = 0
    while i < len(body):
        while i < len(body) and (body[i].isspace() or body[i] == ","):
            i += 1
        if i >= len(body):
            break
        field_match = _FIELD_RE.match(body, i)
        if not field_match:
            # Skip to next field separator.
            comma = body.find(",", i)
            if comma == -1:
                break
            i = comma + 1
            continue
        name = field_match.group("name").lower()
        value, after = _read_value(body, field_match.end())
        fields[name] = value.strip()
        i = after
    return fields


def parse_bibtex(text: str) -> list[BibEntry]:
    """Return one `BibEntry` per top-level `@type{...}` block."""
    entries: list[BibEntry] = []
    i = 0
    while i < len(text):
        header = _ENTRY_HEADER_RE.search(text, i)
        if not header:
            break
        body_start = header.end()
        # Find the matching closing brace for the entry header's opening `{`.
        # The header consumed `{<key>,` so we are now inside the entry body.
        depth = 1
        j = body_start
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            break
        body = text[body_start:j]
        fields = _parse_fields(body)
        entries.append(
            BibEntry(
                cite_key=header.group("key"),
                entry_type=header.group("type").lower(),
                fields=fields,
                source_text=text[header.start() : j + 1],
            )
        )
        i = j + 1
    return entries
