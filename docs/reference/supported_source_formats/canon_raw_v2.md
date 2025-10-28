---
tags:
  - .cr2
  - extension
  - time by metadata
  - coords by correlation
  - gallery image
---

# Canon Raw v2 (CR2)

## Description

Canon Raw v2 (CR2) files are processed similarly to common image formats, with full EXIF metadata extraction for timestamps and GPS coordinates when available.

## File Extensions

- `.cr2` - Canon Raw Version 2 format

## Processing Details

### Time Extraction (Priority Order)

1. **EXIF Metadata** (Primary): `EXIF:CreateDate` field in `YYYY:MM:DD HH:MM:SS` format
2. **Filename Parsing** (Fallback): Extracts numeric sequences from filename  
3. **File Modification Time** (Last Resort): Uses the file's `mtime` when other methods fail

### Coordinate Extraction

1. **EXIF GPS Metadata** (Primary): 
   - `Composite:GPSLatitude` 
   - `Composite:GPSLongitude`
   - Full GPS metadata from camera when available
2. **Time-Based Correlation** (Fallback): Matches CR2 timestamp with nearest GPS track point from GPX files

### RAW Processing

- **Format Conversion**: CR2 files are converted to the configured output format (default: JPG)
- **Quality Settings**: Configurable via `image_options` in configuration
- **EXIF Preservation**: Metadata extraction occurs before conversion
- **Unique Naming**: Duplicate filenames handled with automatic counter suffixes

## Configuration

```yaml
site:
  image_format: jpg                  # Output format for converted RAW files
  image_options: {}                  # PIL/Pillow save options for conversion

features:
  geo_correlation:                   # For coordinate fallback
    enabled: true
    time_offset: !duration 0 seconds         # Camera time offset
    max_time_diff: !duration 300 seconds     # Max correlation window
```

## Dependencies

- **ExifTool**: Required for CR2 metadata extraction
- **PIL/Pillow**: For RAW to standard format conversion
  - Note: CR2 support may require additional libraries or plugins

## Tips for Best Results

- **Camera GPS**: Enable GPS logging on Canon cameras when available
- **Time Synchronization**: Keep camera time synced with GPS device for accurate correlation
- **External GPS**: Use external GPS logger alongside camera for location data
- **RAW Benefits**: CR2 files often contain more complete EXIF metadata than processed formats

## Camera Compatibility

Canon cameras that produce CR2 files, including:
- Canon EOS DSLR series
- Canon PowerShot series (select models)
- Most Canon cameras from ~2004 onwards

## Output

- **Gallery Images**: Converted images appear in the photo gallery
- **Metadata Preservation**: Timestamps and GPS coordinates extracted and preserved
- **Web Optimization**: Converted to web-friendly formats while maintaining quality
- **Location Integration**: GPS metadata used for map display and correlation with other assets