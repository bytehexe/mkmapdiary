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

* Show journal icons on map (icon book-solid/microphone-solid; marker cluster: keyframes-couple-solid, over 10: keyframes-solid)
* Adjust color palette for map data
* Write documentation
  * General workings
  * Asset database
  * Deferred task for gpx
  * All supported file types