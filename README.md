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
mkmapdiary traveljournal
x-www-browser traveljournal_dist/index.html # Open the page
```

Mkmapdiary will then create a directory `traveljournal_dist`, containing the output as a website.

For the full reference of commandline options run `mkmapdiary --help`.

## Running mkmapdiary on placeholder data

Mkmapdiary can generate a project with placeholder data:

```bash
mkmapdiary -T demo
mkmapdiary demo
x-www-browser demo/index.html
```

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