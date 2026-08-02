import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mkmapdiary.lib.credits import (
    canonical_name,
    packages_from_report,
    resolved_packages,
)

REPORT = Path(__file__).parent / "fixtures" / "pip_report.json"


def _report() -> dict[str, Any]:
    return json.loads(REPORT.read_text())


def test_report_yields_all_packages() -> None:
    packages = packages_from_report(_report())

    assert {canonical_name(p.name) for p in packages} == {
        "click",
        "poiidx",
        "pyexiftool",
    }


def test_report_reads_versions() -> None:
    packages = {canonical_name(p.name): p for p in packages_from_report(_report())}

    assert packages["click"].version == "8.1.7"
    assert packages["poiidx"].version == "0.0.8"


def test_report_uses_the_same_license_rules_as_installed_metadata() -> None:
    packages = {canonical_name(p.name): p for p in packages_from_report(_report())}

    assert packages["poiidx"].license == "MIT"
    assert packages["click"].license == "BSD License"
    # the election table applies here too
    assert packages["pyexiftool"].license == "BSD-3-Clause"


def test_report_reads_urls() -> None:
    packages = {canonical_name(p.name): p for p in packages_from_report(_report())}

    assert packages["poiidx"].url == "https://github.com/bytehexe/poiidx"
    assert packages["click"].url == "https://github.com/pallets/click"


def test_empty_report_yields_nothing() -> None:
    assert packages_from_report({"install": []}) == []


def test_resolved_packages_defaults_to_no_prerelease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        captured["command"] = command
        return SimpleNamespace(stdout='{"install": []}')

    monkeypatch.setattr(subprocess, "run", fake_run)

    resolved_packages()

    assert "--pre" not in captured["command"]


def test_resolved_packages_allow_prerelease_adds_pre_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        captured["command"] = command
        return SimpleNamespace(stdout='{"install": []}')

    monkeypatch.setattr(subprocess, "run", fake_run)

    resolved_packages("mkmapdiary[all]", allow_prerelease=True)

    assert "--pre" in captured["command"]
