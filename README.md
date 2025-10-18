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

* Write documentation
  * General workings
  * Asset database
  * Deferred task for gpx
  * All supported file types