# Dev commands

## Running the dev version

```
hatch run mkmapdiary
```

## Pruning the enviroments

```
hatch env prune
```

## Installing pre-commit

```
pre-commit install
```

## Updating the locale files
```
msgfmt src/mkmapdiary/locale/de/LC_MESSAGES/messages.po -o src/mkmapdiary/locale/de/LC_MESSAGES/messages.mo
```