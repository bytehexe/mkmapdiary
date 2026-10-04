# mkmapdiary

[![PyPI - Version](https://img.shields.io/pypi/v/mkmapdiary.svg)](https://pypi.org/project/mkmapdiary)
![PyPI - License](https://img.shields.io/pypi/l/mkmapdiary)
![PyPI - Status](https://img.shields.io/pypi/status/mkmapdiary)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mkmapdiary)


-----

A travel journal generator.

## Installation

```console
pipx install mkmapdiary[all]
```

## Quick start

Set up a directory containing all your sources, e.g. `traveljournal`. Then run:

```bash
mkmapdiary build traveljournal
```

Mkmapdiary will then create a directory `traveljournal_dist`, containing the output as a
website. Open it by double-clicking the `Open on Linux.sh` / `Open on Mac.command` /
`Open on Windows.bat` script at the top of that directory for your platform — it starts a
small bundled local server and opens the journal in your browser (needed for OpenStreetMap's
tile policy, which requires `http://` rather than `file://`). Set
`features.bundle_viewer_server.enabled: false` in the project config to go back to the
old flat layout with `index.html` at the top, opened directly via `file://`:

```bash
x-www-browser traveljournal_dist/index.html # with bundle_viewer_server disabled
```

For the full reference of commandline options run `mkmapdiary --help` or `mkmapdiary build --help`.

## Running mkmapdiary on placeholder data

Mkmapdiary can generate a project with placeholder data:

```bash
mkmapdiary generate-demo demo
mkmapdiary build demo
```

Then open `demo_dist/Open on Linux.sh` (or the Mac/Windows equivalent) as above.
This is for debugging/demonstration purposes only! Images by https://picsum.photos/.

## Running the dev version

Within the project root, run:

```bash
pipx install hatch taskipy pre-commit
pre-commit install
hatch run mkmapdiary --help
```

## Documentation

See https://bytehexe.github.io/mkmapdiary/

## License

`mkmapdiary` is distributed under the terms of the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) license.

> Required Notice: Copyright Janna Hopp (https://github.com/bytehexe)

## Bon voyage!

Have fun travelling and stay safe!