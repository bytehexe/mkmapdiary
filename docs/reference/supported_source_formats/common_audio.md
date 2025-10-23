---
tags:
  - identify
  - audio
  - time by filename/mtime
  - journal entry
  - coords by correlation
---

# Common audio formats

## Description

Audio files are processed to create journal entries with automatic transcription and AI-generated titles. They support coordinate correlation through GPS track matching.

## Supported Formats

All audio formats supported by `pydub.AudioSegment`, including:
- WAV (`.wav`)
- MP3 (`.mp3`) 
- FLAC (`.flac`)
- M4A (`.m4a`)
- OGG (`.ogg`)
- And other formats supported by FFmpeg

## Processing Details

### Time Extraction

1. **Filename Parsing** (Primary): Extracts numeric sequences from filename (e.g., `note_20200101_040820.wav` → 2020-01-01 04:08:20)
2. **File Modification Time** (Fallback): Uses the file's `mtime` when filename parsing fails

### Coordinate Extraction

**Time-Based Correlation Only**: Audio files rely entirely on time correlation with GPS tracks. The system matches the audio timestamp with the nearest GPS track point within the configured time window.

### Audio Processing

1. **Format Conversion**: All audio is converted to MP3 format for web compatibility
2. **Transcription** (Optional): 
   - Automatic speech-to-text using AI/Ollama
   - Creates timestamped segments
   - Generates searchable text content
3. **Title Generation**: AI analyzes transcribed content to create descriptive titles
4. **Web Player**: Creates interactive audio player with transcript display

## Configuration

```yaml
features:
  transcription: "auto"              # Enable/disable transcription

ollama_ai_model: "llama3:8b"         # Model for transcription and titles

ai:
  generate_title:                    # Title generation settings
    prompt: |
      Create exactly one title that summarizes the following text...
    options:
      temperature: 0.2
      top_p: 0.8

geo_correlation:                     # For coordinate correlation
  timezone: "UTC"
  time_offset: 0                     # Audio device time offset (seconds)
  max_time_diff: 300                 # Max correlation window (seconds)
```

## Dependencies

- **pydub**: Audio format conversion
- **FFmpeg**: Backend for audio processing  
- **Ollama**: AI transcription and title generation (optional)

## Tips for Best Results

- **Naming Convention**: Use timestamp-based filenames for accurate time extraction
- **Time Synchronization**: Keep audio recording device time synced with GPS device
- **Transcription Quality**: Clear audio and supported language improve AI transcription accuracy
- **GPS Logging**: Maintain GPS tracks during audio recording for location data

## Output

- **Audio Player**: Interactive web-based player in journal entries
- **Transcription**: Searchable text content with timestamps
- **AI Titles**: Automatically generated descriptive titles based on content
- **Location Data**: Coordinates from GPS correlation (when available)