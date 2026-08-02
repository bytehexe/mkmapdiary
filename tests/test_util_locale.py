import pytest

from mkmapdiary.util.locale import auto_detect_locale

ENV_VARS = ("LC_ALL", "LC_CTYPE", "LANG")


def _clear_all(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_lc_all_wins_over_lc_ctype_and_lang(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_all(monkeypatch)
    monkeypatch.setenv("LC_ALL", "de_DE.UTF-8")
    monkeypatch.setenv("LC_CTYPE", "fr_FR.UTF-8")
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    assert auto_detect_locale() == "de_DE.UTF-8"


def test_lc_ctype_used_when_lc_all_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_all(monkeypatch)
    monkeypatch.setenv("LC_CTYPE", "fr_FR.UTF-8")
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    assert auto_detect_locale() == "fr_FR.UTF-8"


def test_lang_used_when_others_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_all(monkeypatch)
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    assert auto_detect_locale() == "en_US.UTF-8"


def test_none_when_all_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_all(monkeypatch)

    assert auto_detect_locale() is None


@pytest.mark.parametrize("value", ["C", "POSIX", "C.UTF-8", "POSIX.UTF-8"])
def test_none_for_language_less_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    _clear_all(monkeypatch)
    monkeypatch.setenv("LANG", value)

    assert auto_detect_locale() is None


def test_value_without_encoding_returned_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_all(monkeypatch)
    monkeypatch.setenv("LANG", "de_DE")

    assert auto_detect_locale() == "de_DE"
