"""Tests for _parse_iso_date -- the parsing contract of IsoDateEntry.

No tkinter import here, deliberately: these run without a display, unlike
tests/test_ui_date_entry.py, which requires tk.Tk() and skips headlessly
(including in CI). Importing mkmapdiary.ui itself is safe without a display
-- it pulls in sv_ttk/darkdetect, which the hatch-test env has via the "ui"
feature -- only instantiating tk.Tk() needs one.
"""

import datetime

import pytest

from mkmapdiary.ui import _parse_iso_date


def test_parses_a_valid_date() -> None:
    assert _parse_iso_date("2026-08-02") == datetime.date(2026, 8, 2)


def test_tolerates_surrounding_whitespace() -> None:
    assert _parse_iso_date("  2026-08-02  ") == datetime.date(2026, 8, 2)


def test_empty_string_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _parse_iso_date("")


def test_malformed_value_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _parse_iso_date("not-a-date")
