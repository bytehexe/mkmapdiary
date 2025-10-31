# Mkmapdiary

A travel journal generator that transforms your GPS tracks, notes, and photos into beautiful, interactive travel websites.

## What is mkmapdiary?

Mkmapdiary is a Python tool that automatically creates travel journals from your raw travel data. Whether you're documenting a weekend hike, a cross-country road trip, or a multi-week adventure, mkmapdiary helps you turn your GPS tracks, photos, and notes into a web-based diary.

## Key Features

- **📍 GPS Track Visualization**: Interactive maps displaying your routes and points of interest
- **📝 Note Integration**: Combines your text notes and markdown files with location data
- **📸 Photo Gallery**: Automatically organizes and displays your travel photos
- **🎤 Audio Transcription**: Converts voice recordings into searchable text
- **🌐 Static Website Generation**: Creates fast, self-contained websites that work anywhere
- **📱 Mobile-Friendly**: Responsive design that looks great on all devices
- **📦 No Server Required**: No need for webserver installation - share via ZIP file or USB stick

## Quick Start

Install mkmapdiary with all optional dependencies:

```bash
pipx install mkmapdiary[all]
```

Generate a travel journal from your data directory:

```bash
mkmapdiary build your_travel_data/
x-www-browser your_travel_data_dist/index.html
```

## Try the Demo

Want to see mkmapdiary in action? Generate a demo project with sample data:

```bash
mkmapdiary generate-demo demo
mkmapdiary build demo
x-www-browser demo_dist/index.html
```

## Getting Help

- Browse the [supported file formats](reference/supported_source_formats/) 
- See [development documentation](reference/development/) if you want to contribute

## Repository

You can find the mkmapdiary source code on [GitHub](https://github.com/bytehexe/mkmapdiary).

## License

Mkmapdiary is distributed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

<!--

## Tutorial

**Ready to start your digital travel journal?** Head over to the [Tutorial](tutorial/) to begin your journey!

-->