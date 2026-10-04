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


def test_miniserve_entry_has_the_pinned_version() -> None:
    # credits.py duplicates this constant rather than importing viewerServer
    # (see BUNDLED_BINARY_VERSIONS's comment) -- this test is what keeps the
    # two from drifting apart.
    from mkmapdiary.lib.viewerServer import _MINISERVE_VERSION

    result = bundled_binary_credits(enabled=True)
    miniserve = next(p for p in result if p.name == "miniserve")
    assert miniserve.version == _MINISERVE_VERSION
