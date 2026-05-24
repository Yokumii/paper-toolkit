from pathlib import Path

import pytest

from paper_toolkit.io import write_atomic_text


def test_write_atomic_text_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "out.json"
    write_atomic_text(target, '{"hello": "world"}\n')
    assert target.read_text(encoding="utf-8") == '{"hello": "world"}\n'


def test_write_atomic_text_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("old", encoding="utf-8")
    write_atomic_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_write_atomic_text_leaves_no_tmp_files_after_success(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    write_atomic_text(target, "hello")
    leftovers = [p for p in tmp_path.iterdir() if p.name != "x.txt"]
    assert leftovers == []


def test_write_atomic_text_cleans_tmp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os as _os

    real_replace = _os.replace

    def boom(src: str, dst: str) -> None:
        raise OSError("synthetic failure")

    monkeypatch.setattr(_os, "replace", boom)
    target = tmp_path / "x.txt"
    with pytest.raises(OSError, match="synthetic failure"):
        write_atomic_text(target, "hello")
    # Restore so cleanup of pytest tmp_path can succeed.
    monkeypatch.setattr(_os, "replace", real_replace)
    leftovers = list(tmp_path.iterdir())
    assert leftovers == []  # no orphan .tmp file
    assert not target.exists()
