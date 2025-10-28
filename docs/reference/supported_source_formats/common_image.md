---
tags:
  - identify
  - time by metadata
  - coords by metadata
  - coords by correlation
  - time by filename/mtime
  - gallery image
---

# Common image formats

## Description

Common image formats are identified automatically using the [`identify` library](https://pypi.org/project/identify/) and processed to extract timestamps and GPS coordinates from EXIF metadata when available.

## Supported Formats

All image formats supported by the identify library, including:
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`) 
- TIFF (`.tiff`, `.tif`)
- BMP (`.bmp`)
- And many others recognized by the identify library

## Processing Details

### Time Extraction (Priority Order)

1. **EXIF Metadata** (Primary): `EXIF:CreateDate` field in `YYYY:MM:DD HH:MM:SS` format
2. **Filename Parsing** (Fallback): Extracts numeric sequences from filename (e.g., `photo_20200101_012709.jpg` → 2020-01-01 01:27:09)
3. **File Modification Time** (Last Resort): Uses the file's `mtime` when other methods fail

### Coordinate Extraction

1. **EXIF GPS Metadata** (Primary): 
   - `Composite:GPSLatitude` 
   - `Composite:GPSLongitude`
2. **Time-Based Correlation** (Fallback): Matches image timestamp with nearest GPS track point from GPX files within configurable time window

### Image Processing

- **Format Conversion**: Images are converted to the configured output format (default: JPG)
- **Quality Settings**: Configurable via `image_options` in configuration
- **Unique Naming**: Duplicate filenames are handled with automatic counter suffixes

## Configuration

```yaml
site:
  image_format: jpg                  # Output format
  image_options: {}                  # PIL/Pillow save options

features:
  geo_correlation:                   # For coordinate fallback
    enabled: true
    time_offset: !duration 0 seconds         # Camera time offset
    max_time_diff: !duration 300 seconds     # Max correlation window
```

## Dependencies

- **ExifTool**: Required for EXIF metadata extraction
- **PIL/Pillow**: For image processing and format conversion

## Tips for Best Results

- **Camera Time Sync**: Ensure your camera time matches GPS device time for accurate coordinate correlation
- **Filename Conventions**: Use timestamp-based filenames when EXIF data is unavailable
- **GPS Logging**: Keep GPS tracks running when taking photos for automatic coordinate correlation

## Output

Images appear in the photo gallery with extracted timestamps and coordinates (when available) used for chronological organization and map display.