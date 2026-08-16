# Dependencies

These dependencies cannot be installed with pip and must be present on the system:

* ffmpeg or avconv (for pydub)
* ollama (for llms)
* gpsbabel (for conversion of geo formats)
* exiftool (for reading image metadata via pyexiftool)
* pico2wave (for synthesizing demo audio in the `generate-demo` command)
* PostgreSQL with PostGIS (only when `features.poi_detection` is enabled; see
  [How to Set Up POI Detection](../how-to_guides/setup-poi-detection.md))

Building the project documentation additionally needs PlantUML and a Java runtime, for
the task dependency diagram.

See [Credits](credits.md) for the open source packages resolved via pip.
