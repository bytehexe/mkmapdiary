---
tags:
  - identify
  - journal entry
  - time by filename/mtime
  - markdown
  - coords by correlation
---

# Markdown

## Description

Markdown files are processed as journal entries, preserving their original formatting while extracting timestamps for chronological organization and coordinate correlation.

## File Extensions

Files identified with the `markdown` tag by the [`identify` library](https://pypi.org/project/identify/), typically:
- `.md`
- `.markdown`
- `.mdown`

## Processing Details

### Time Extraction

1. **Filename Parsing** (Primary): Extracts numeric sequences from filename (e.g., `note_20200103_085834.md` → 2020-01-03 08:58:34)
2. **File Modification Time** (Fallback): Uses the file's `mtime` when filename parsing fails

!!! note "Future Enhancement"
    Front-matter timestamp parsing is planned but not yet implemented. Currently, time extraction relies on filename patterns and file modification time.

### Coordinate Extraction

**Time-Based Correlation Only**: Markdown files rely entirely on time correlation with GPS tracks. The system matches the markdown file timestamp with the nearest GPS track point within the configured time window.

### Markdown Processing

1. **Direct Copy**: Markdown files are copied as-is to the build directory
2. **Unique Naming**: Duplicate filenames are handled with automatic counter suffixes
3. **Format Preservation**: All original markdown formatting, links, and structure are maintained
4. **Asset Integration**: Files become part of the journal entry system

## Configuration

```yaml
geo_correlation:                     # For coordinate correlation
  timezone: "UTC"
  time_offset: 0                     # Markdown creation time offset (seconds)
  max_time_diff: 300                 # Max correlation window (seconds)
```

## Tips for Best Results

- **Naming Convention**: Use timestamp-based filenames for accurate time extraction
- **Time Synchronization**: Keep markdown creation time synced with GPS device time  
- **Content Organization**: Use standard markdown formatting for consistent display
- **GPS Logging**: Maintain GPS tracks when creating markdown notes for location data

## Future Enhancements

- **Front-matter Support**: Planned support for extracting timestamps from YAML front-matter
- **Metadata Extraction**: Additional metadata parsing from front-matter headers

## Output

- **Journal Entries**: Rendered markdown content in chronological journal pages
- **Preserved Formatting**: All markdown syntax rendered properly in the final output
- **Location Data**: Coordinates from GPS correlation (when available)
- **Searchable Content**: Markdown content becomes part of searchable journal
