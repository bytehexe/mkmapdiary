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

* Add approx tagging for assets using gps data (with adjustable offset)
* Add AI summary to day pages
* Write documentation
  * General workings
  * Asset database
  * Deferred task for gpx
  * All supported file types