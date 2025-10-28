---
tags:
  - identify
  - gpx
  - map feature
  - time by content
  - coords by content
---

# GPS Exchange Format

## Description

GPX (GPS Exchange Format) files contain GPS track data with waypoints, tracks, and routes. mkmapdiary processes these files to create map features and provide coordinate data for time-based correlation with other assets.

## File Extensions

- `.gpx`

## Processing Details

### Time and Coordinate Extraction

Time and coordinates are extracted directly from GPX elements:

- **Waypoints** (`<wpt>`): Latitude, longitude from attributes, timestamp from `<time>` element
- **Track Points** (`<trkpt>`): Latitude, longitude, elevation, and timestamps from track segments
- **Route Points** (`<rtept>`): Similar to waypoints but for planned routes

### File Processing

GPX files are processed in several stages:

1. **Date Collection**: All timestamps in the GPX file are analyzed to determine which dates are covered
2. **File Splitting**: Large GPX files are split by date, creating separate daily GPX files
3. **Merging**: Multiple GPX sources for the same date are merged into unified daily files
4. **Asset Generation**: Final GPX files are placed in the assets directory with date-based naming (`YYYY-MM-DD.gpx`)

### Coordinate Correlation

GPX files serve as the primary source for coordinate correlation. Other file types (images, audio, text) without embedded GPS data can be matched to GPX track points based on timestamps within a configurable time window (default: 300 seconds).

## Configuration

Coordinate correlation behavior can be configured via the `geo_correlation` section:

```yaml
features:
  geo_correlation:
    enabled: true
    time_offset: !duration 0 seconds       # Time offset 
    max_time_diff: !duration 300 seconds   # Maximum time difference for correlation
```

## Output

- **Map Features**: Tracks and waypoints displayed on the interactive map
- **Coordinate Source**: Provides location data for other assets through time correlation