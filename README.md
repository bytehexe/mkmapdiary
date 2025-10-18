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

* Add approx tagging for assets using gps data (with timezone and adjustable offset; gobally and per asset type)
* Show journal icons on map (icon book-solid/microphone-solid; marker cluster: keyframes-couple-solid, over 10: keyframes-solid)
* Adjust color palette for map data
* Add AI summary to day pages?
* Write documentation
  * General workings
  * Asset database
  * Deferred task for gpx
  * All supported file types