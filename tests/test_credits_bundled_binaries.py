from mkmapdiary.lib.credits import bundled_binary_credits


def test_includes_miniserve_when_enabled() -> None:
    result = bundled_binary_credits(enabled=True)
    names = {package.name for package in result}
    assert "miniserve" in names


def test_empty_when_disabled() -> None:
    assert bundled_binary_credits(enabled=False) == []


def test_miniserve_entry_has_license_and_homepage() -> None:
    result = bundled_binary_credits(enabled=True)
    miniserve = next(p for p in result if p.name == "miniserve")
    assert miniserve.license == "MIT"
    assert miniserve.url == "https://github.com/svenstaro/miniserve"
