---
tags:
  - extension
  - coords by content
  - time by content
  - map feature
  - .poi
  - .bin
---

# Qstarz BL-1000

## Description

The Qstarz BL-1000 is a GPS data logger that creates proprietary binary format files. mkmapdiary converts these files to standard GPX format using GPSBabel for processing as map features.

## Supported File Extensions

- `.bin` - Binary GPS log files from Qstarz BL-1000
- `.poi` - Point of Interest files from Qstarz BL-1000  
- `.dat` - Data files (ignored - not directly supported by GPSBabel)

## Processing Details

### Conversion Process

1. **GPSBabel Conversion**: Binary files are converted to GPX format using the GPSBabel tool
2. **Command Used**: `gpsbabel -t -w -r -i qstarz_bl-1000 -f input.bin -o gpx -F output.gpx`
3. **GPX Processing**: Converted files are then processed as standard GPX files

### Time and Coordinate Extraction

After conversion to GPX format:
- **Time Data**: Extracted from converted GPX track points and waypoints
- **Coordinate Data**: Latitude, longitude, and elevation from GPS logging
- **Track Information**: Complete GPS tracks with timestamps for route visualization

### File Processing Workflow

1. **Detection**: Files identified by `.bin` and `.poi` extensions
2. **Intermediate Conversion**: Creates temporary GPX files in the files directory
3. **GPX Processing**: Converted files processed through the standard GPX handler
4. **Asset Generation**: Final output follows GPX format processing (date-based splitting, etc.)

## Dependencies

- **GPSBabel**: Required for converting proprietary Qstarz formats to GPX
  - Must be installed and available in system PATH
  - Supports Qstarz BL-1000 format (`qstarz_bl-1000` driver)

## Configuration

No specific configuration required. Processing follows GPX configuration settings after conversion:

```yaml
features:
  geo_correlation:                   # Applied after conversion
    enabled: true
    time_offset: !duration 0 seconds         # GPS device time offset
    max_time_diff: !duration 300 seconds     # Max correlation window
```

## Installation Requirements

```bash
# Ubuntu/Debian
sudo apt-get install gpsbabel

# macOS
brew install gpsbabel

# Or compile from source: https://www.gpsbabel.org/
```

## Tips for Best Results

- **Device Settings**: Ensure Qstarz BL-1000 is configured with appropriate logging intervals
- **File Management**: Keep original binary files as backup; conversion creates intermediate GPX files
- **Time Accuracy**: Qstarz devices typically maintain accurate GPS time automatically
- **Battery Management**: Ensure device has sufficient power during logging sessions

## Output

After conversion and processing:
- **Map Features**: GPS tracks and waypoints displayed on the interactive map
- **Coordinate Source**: Provides location data for other assets through time correlation  
- **Daily GPX Files**: Converted data merged into date-based GPX files in assets directory