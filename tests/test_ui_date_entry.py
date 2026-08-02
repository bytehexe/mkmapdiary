from __future__ import annotations

import datetime
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import tkinter as tk
else:
    tk = pytest.importorskip("tkinter")


@pytest.fixture
def root() -> Generator[tk.Tk, None, None]:
    """A hidden Tk root, skipped when no display is available."""
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    r.withdraw()
    yield r
    r.destroy()


def test_get_date_parses_iso(root: tk.Tk) -> None:
    from mkmapdiary.ui import IsoDateEntry

    entry = IsoDateEntry(root)
    entry.delete(0, "end")
    entry.insert(0, "2026-08-02")

    assert entry.get_date() == datetime.date(2026, 8, 2)


def test_defaults_to_today(root: tk.Tk) -> None:
    from mkmapdiary.ui import IsoDateEntry

    entry = IsoDateEntry(root)

    assert entry.get_date() == datetime.date.today()


def test_invalid_date_raises_value_error(root: tk.Tk) -> None:
    from mkmapdiary.ui import IsoDateEntry

    entry = IsoDateEntry(root)
    entry.delete(0, "end")
    entry.insert(0, "not-a-date")

    with pytest.raises(ValueError):
        entry.get_date()
