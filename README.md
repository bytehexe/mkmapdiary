# Tdgen readme

## Update dependencies
```
pipenv install
```

## Run
```
pipenv run python -m tdgen
```

## Update locale files
```
msgfmt tdgen/locale/de/LC_MESSAGES/messages.po -o tdgen/locale/de/LC_MESSAGES/messages.mo
```

## Todo

* Refactor clusters: move them out of the GPX file
* Add approx tagging for photos using gps data (with adjustable offset)
  * same for journal entries
* Add AI summary to day pages
* Add metadata to journal entries (datetime and place, if available)