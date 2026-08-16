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

The same RAW handler covers every extension listed under `input_formats.raw.formats`:

- `.cr2` - Canon Raw Version 2 format
- `.cr3`, `.crw` - other Canon RAW formats
- `.nef`, `.nrw` - Nikon
- `.arw`, `.sr2`, `.srf` - Sony

Anything LibRaw can read can be added there; the value is ignored as long as it is not
`null`, which disables the extension.

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

- **Development**: `rawpy` (LibRaw) develops the RAW to an 8-bit RGB image using the
  camera white balance and automatic brightness, and `imageio` writes an intermediate
  JPEG
- **Thumbnail shortcut**: With `features.cr2.use_thumbnail`, the embedded preview JPEG is
  extracted instead of developing the RAW. Much faster, but limited to the resolution and
  in-camera processing of that preview
- **Format Conversion**: The intermediate JPEG then goes through the normal image
  pipeline and ends up in the configured output format (default: JPG)
- **Quality Settings**: Configurable via `image_options` in configuration
- **EXIF Preservation**: Metadata is read from the original RAW, not from the
  intermediate JPEG
- **Unique Naming**: Duplicate filenames handled with automatic counter suffixes

## Configuration

```yaml
site:
  image_format: jpg                  # Output format for converted RAW files
  image_options: {}                  # PIL/Pillow save options for the final image

features:
  cr2:
    use_thumbnail: false             # true = extract the embedded preview instead of developing
  geo_correlation:                   # For coordinate fallback
    max_time_diff: !duration 300 seconds     # Max correlation window
```

Camera clock offsets go into a [`calibration.yaml`](../calibration.md);
`features.geo_correlation.time_offset` is not implemented.

## Dependencies

- **ExifTool**: Required for CR2 metadata extraction
- **rawpy** (LibRaw): RAW decoding and development
- **imageio**: Writes the intermediate JPEG
- **PIL/Pillow**: Final image conversion and saving

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