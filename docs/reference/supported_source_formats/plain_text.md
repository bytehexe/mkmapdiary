---
tags:
  - identify
  - journal entry
  - time by filename/mtime
  - plain-text
  - coords by correlation
---

# Plain Text

## Description

Plain text files are converted to journal entries with AI-generated titles and markdown formatting. They support coordinate correlation through GPS track matching.

## File Extensions

Files identified with the `plain-text` tag by the [`identify` library](https://pypi.org/project/identify/), typically:
- `.txt`
- Files with text content and no specific format markers

## Processing Details

### Time Extraction

1. **Filename Parsing** (Primary): Extracts numeric sequences from filename (e.g., `note_20200101_074736.txt` → 2020-01-01 07:47:36)
2. **File Modification Time** (Fallback): Uses the file's `mtime` when filename parsing fails

### Coordinate Extraction

**Time-Based Correlation Only**: Text files rely entirely on time correlation with GPS tracks. The system matches the text file timestamp with the nearest GPS track point within the configured time window.

### Text Processing

1. **Content Analysis**: Reads the entire text file content
2. **Title Generation**: AI analyzes text content to create descriptive titles
3. **Markdown Conversion**: Wraps content in a markdown template with generated title
4. **Template Formatting**: Uses configurable template (`md_text.j2`) for consistent formatting

## Configuration

```yaml
strings:
  text_title: null                   # Custom prefix for text entries (or null for default)

ollama_ai_model: "llama3:8b"         # Model for title generation

ai:
  generate_title:                    # Title generation settings
    prompt: |
      Create exactly one title that summarizes the following text in {locale}.
      The title must be a single phrase, 3–5 words long...
    options:
      temperature: 0.2
      top_p: 0.8

geo_correlation:                     # For coordinate correlation
  timezone: "UTC"
  time_offset: 0                     # Text device time offset (seconds)
  max_time_diff: 300                 # Max correlation window (seconds)
```

## Dependencies

- **Ollama**: AI title generation

## Tips for Best Results

- **Naming Convention**: Use timestamp-based filenames for accurate time extraction  
- **Time Synchronization**: Keep text creation time synced with GPS device time
- **Content Quality**: Clear, descriptive text helps AI generate better titles
- **GPS Logging**: Maintain GPS tracks when creating text notes for location data

## Output

- **Journal Entries**: Formatted markdown with AI-generated titles
- **Text Content**: Original text preserved and formatted
- **Location Data**: Coordinates from GPS correlation (when available)
- **Searchable Content**: Text becomes part of searchable journal content