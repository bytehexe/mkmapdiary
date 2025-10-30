# Configuration Reference

mkmapdiary uses YAML configuration files to customize its behavior. Configuration can be specified in several places with increasing precedence:

1. Built-in defaults
2. User configuration file (`~/.config/mkmapdiary/config.yaml`)
3. Project configuration file (`config.yaml` in source directory)
4. Command-line parameters (`-x key=value`)

## Configuration Schema

### Top-Level Structure

```yaml
features:              # Feature configuration
site:                  # Site generation settings  
strings:               # Custom translation strings
llm_prompts:           # LLM prompt templates
```

### Features Section

Controls which features are enabled and their behavior.

```yaml
features:
  transcription:
    enabled: !auto transcription.enabled    # Auto-detect or boolean
    user_cache: false                       # Cache transcriptions in user directory
  
  llms:
    enabled: true                           # Enable LLM features
    text_model: "llama3:8b"                # Model for text operations
  
  geo_correlation:
    enabled: true                           # Enable coordinate correlation
    time_offset: !duration 0 seconds       # Time synchronization offset
    max_time_diff: !duration 300 seconds   # Maximum correlation window
  
  poi_detection:
    enabled: true                           # Enable POI detection
    max_age: !duration 300 days            # Maximum age for POI data
```

### Site Section

Controls website generation and appearance.

```yaml
site:
  image_format: jpg                         # Output image format (jpg, png, webp)
  image_options: {}                         # PIL/Pillow save options
  locale: !auto site.locale                # Auto-detect or locale string
  timezone: !auto site.timezone            # Auto-detect or timezone string
```

### Strings Section

Override default text strings in the generated site.

```yaml
strings:
  journal_title: null                       # Custom journal title (null = default)
  site_name: null                          # Custom site name
  map_title: null                          # Custom map page title
  days_title: null                         # Custom daily overview title
  audio_title: null                        # Custom audio section title
  text_title: null                         # Custom text section title
  gallery_title: null                      # Custom gallery title
  home_title: null                         # Custom home page title
```

### LLM Prompts Section

Customize prompts for AI features.

```yaml
llm_prompts:
  generate_title:
    prompt: |
      Create exactly one title that summarizes the following text in {locale}.
      The title must be a single phrase, 3–5 words long.
      Use only words or phrases, or concepts that appear in the text.
      If the text contains multiple topics, combine them in a single title, separated naturally (e.g., with commas or conjunctions).
      Focus on the most important topics if all cannot fit in the title.
      Do not produce multiple titles, or explanations.
      Do not include phrases like 'Here is' or 'Summary'.
      If the text is empty or does not contain any useful information, leave your response empty.
      Do not invent information not present in the text.
      Output only the title, nothing else.

      Text:
      {text}
    options:
      temperature: 0.2                      # LLM temperature (0-2)
      top_p: 0.8                           # LLM top-p value (0-1)
      # seed: 42                           # Optional: random seed for reproducibility
  
  generate_tags:
    prompt: |
      Extract a list of relevant tags in {locale} from the following text.
      The list should not exceed 15 tags.
      Produce a single list of tags, separated by commas.
      Do not include explanations or additional text.
      Output only the list of tags, nothing else.
      If the text is empty or does not contain any useful information, leave your response empty.
      Do not include phrases like 'Tags:' or 'The tags are'.

      Text:
      {text}
    options:
      temperature: 0.8
      top_p: 0.8
```

## Special Tags

### !auto Tag

The `!auto` tag enables automatic detection of system values:

- `!auto transcription.enabled` - Auto-detect transcription capabilities
- `!auto site.locale` - Use system locale
- `!auto site.timezone` - Use system timezone

### !duration Tag

The `!duration` tag converts human-readable durations to seconds:

- `!duration 0 seconds`
- `!duration 5 minutes`
- `!duration 2 hours`
- `!duration 300 days`

## Command-Line Configuration

Override any configuration value using the `-x` flag with the `build` command:

```bash
# Enable/disable features
mkmapdiary build -x features.transcription.enabled=true source_dir
mkmapdiary build -x features.llms.enabled=false source_dir

# Set model
mkmapdiary build -x features.llms.text_model="llama3:70b" source_dir

# Configure timing
mkmapdiary build -x features.geo_correlation.max_time_diff="!duration 10 minutes" source_dir

# Set site options
mkmapdiary build -x site.image_format=png source_dir
mkmapdiary build -x strings.site_name="My Travel Journal" source_dir
```

You can also use global verbosity options:

```bash
# Verbose output
mkmapdiary -v build source_dir

# Quiet output  
mkmapdiary -q build source_dir
```

## Configuration Files

### User Configuration

Global configuration for all projects:
`~/.config/mkmapdiary/config.yaml`

### Project Configuration

Project-specific configuration:
`config.yaml` in your source directory

Create with:
```bash
# Create project config
mkmapdiary config -x key=value source_dir

# Create user config (affects all projects)
mkmapdiary config --user -x key=value
```

## Examples

### Basic Configuration

```yaml
features:
  llms:
    enabled: true
    text_model: "llama3:8b"
  geo_correlation:
    enabled: true
    max_time_diff: !duration 5 minutes

site:
  image_format: webp
  locale: "en_US.UTF-8"

strings:
  site_name: "My Adventure Journal"
```

### Advanced Configuration

```yaml
features:
  transcription:
    enabled: true
    user_cache: true
  llms:
    enabled: true
    text_model: "llama3:70b"
  geo_correlation:
    enabled: true
    time_offset: !duration 30 seconds
    max_time_diff: !duration 10 minutes
  poi_detection:
    enabled: true
    max_age: !duration 180 days

site:
  image_format: jpg
  image_options:
    quality: 85
    optimize: true
  locale: "de_DE.UTF-8"
  timezone: "Europe/Berlin"

strings:
  site_name: "Reisetagebuch"
  journal_title: "Tagebuch"
  map_title: "Karte"

llm_prompts:
  generate_title:
    prompt: |
      Erstelle genau einen Titel, der den folgenden Text auf Deutsch zusammenfasst.
      Der Titel muss eine einzige Phrase sein, 3-5 Wörter lang.
      
      Text:
      {text}
    options:
      temperature: 0.1
      top_p: 0.9
```