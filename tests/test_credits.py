from email.message import Message

from mkmapdiary.lib.credits import (
    Package,
    canonical_name,
    installed_packages,
    normalise_license,
    project_url,
)


def _metadata(**fields: str | list[str]) -> Message:
    """Build a metadata Message; list values become repeated headers."""
    message = Message()
    for key, value in fields.items():
        header = key.replace("_", "-")
        if isinstance(value, list):
            for item in value:
                message.add_header(header, item)
        else:
            message.add_header(header, value)
    return message


def test_canonical_name_normalises_separators() -> None:
    assert canonical_name("PyExifTool") == "pyexiftool"
    assert canonical_name("mkdocs_material") == "mkdocs-material"
    assert canonical_name("zope.interface") == "zope-interface"


def test_license_expression_wins() -> None:
    md = _metadata(
        Name="poiidx",
        License_Expression="MIT",
        Classifier=["License :: OSI Approved :: BSD License"],
    )
    assert normalise_license(md, "poiidx") == "MIT"


def test_classifiers_used_when_no_expression() -> None:
    md = _metadata(
        Name="requests",
        Classifier=[
            "Programming Language :: Python",
            "License :: OSI Approved :: Apache Software License",
        ],
    )
    assert normalise_license(md, "requests") == "Apache Software License"


def test_multiple_classifiers_joined() -> None:
    md = _metadata(
        Name="tqdm",
        Classifier=[
            "License :: OSI Approved :: MIT License",
            "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        ],
    )
    assert normalise_license(md, "tqdm") == (
        "MIT License; Mozilla Public License 2.0 (MPL 2.0)"
    )


def test_short_license_field_used_as_fallback() -> None:
    md = _metadata(Name="peewee", License="MIT License")
    assert normalise_license(md, "peewee") == "MIT License"


def test_embedded_license_text_falls_through_to_none() -> None:
    md = _metadata(Name="obscure", License="Copyright 2026\n\nPermission is...")
    assert normalise_license(md, "obscure") is None


def test_dual_license_election_overrides_classifiers() -> None:
    """PyExifTool offers GPLv3+ or BSD; mkmapdiary elects BSD."""
    md = _metadata(
        Name="PyExifTool",
        License="GPLv3+/BSD",
        Classifier=[
            "License :: OSI Approved :: BSD License",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        ],
    )
    assert normalise_license(md, "PyExifTool") == "BSD-3-Clause"


def test_project_url_prefers_home_page() -> None:
    md = _metadata(
        Name="x",
        Home_page="https://example.com",
        Project_URL=["Source, https://github.com/example/x"],
    )
    assert project_url(md) == "https://example.com"


def test_project_url_falls_back_to_labelled_entry() -> None:
    md = _metadata(
        Name="x",
        Project_URL=[
            "Tracker, https://example.com/issues",
            "Source, https://example.com/x",
        ],
    )
    assert project_url(md) == "https://example.com/x"


def test_project_url_missing_returns_none() -> None:
    assert project_url(_metadata(Name="x")) is None


def test_installed_packages_includes_root_and_excludes_strays() -> None:
    packages = installed_packages("mkmapdiary")
    names = {canonical_name(p.name) for p in packages}

    assert "mkmapdiary" in names
    assert "click" in names
    # pyinstaller may be present in the environment but is declared by nothing
    assert "pyinstaller" not in names


def test_installed_packages_returns_sorted_packages() -> None:
    packages = installed_packages("mkmapdiary")

    assert all(isinstance(p, Package) for p in packages)
    assert [p.name.lower() for p in packages] == sorted(
        p.name.lower() for p in packages
    )


def test_unknown_root_returns_empty() -> None:
    assert installed_packages("definitely-not-a-package") == []
