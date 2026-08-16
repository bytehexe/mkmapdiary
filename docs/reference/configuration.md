# Configuration Reference

mkmapdiary uses YAML configuration files to customize its behavior. Configuration can be specified in several places with increasing precedence:

1. Built-in defaults
2. User configuration file (`~/.config/mkmapdiary/config.yaml`)
3. Project configuration file (`config.yaml` in source directory)
4. Command-line parameters (`-x key=value`)

Every layer is validated against `resources/config_schema.yaml`, which rejects unknown
keys — a typo in a config file is an error, not a silently ignored setting. The
authoritative defaults live in
[`resources/defaults.yaml`](https://github.com/bytehexe/mkmapdiary/blob/main/src/mkmapdiary/resources/defaults.yaml).

## Configuration Schema

### Top-Level Structure

```yaml
input_formats:         # Which file extensions and identify tags map to which handler
features:              # Feature configuration
site:                  # Site generation settings
debug:                 # Debugging switches
ignore_dates:          # Dates to skip entirely
credits:               # Credits page configuration
strings:               # Custom translation strings
llm_prompts:           # LLM prompt templates
```

### Input Formats Section

Maps input files to the handler that converts them. A key starting with a dot is a file
extension; a key without one is a tag from the
[`identify` library](https://pypi.org/project/identify/). A `null` value ignores the
file.

```yaml
input_formats:
  gpsbabel:
    formats:                    # Value: the -i parameter passed to gpsbabel
      kml: kml                  # Do not add gpx here — it is the internal default format
      .bin: qstarz_bl-1000
      .poi: qstarz_bl-1000
      .dat: null                # Ignored
  raw:
    formats:                    # Value: anything except null, which means ignore
      .cr2: raw
      .cr3: raw
      .crw: raw
      .nef: raw
      .nrw: raw
      .arw: raw
      .sr2: raw
      .srf: raw
```

### Features Section

Controls which features are enabled and their behavior.

```yaml
features:
  cr2:
    use_thumbnail: false                    # Extract the embedded JPEG instead of developing the RAW

  transcription:
    enabled: !auto                          # Auto-detect (true when whisper is installed)

  llms:
    enabled: true                           # Enable LLM features
    text_model: "llama3:8b"                 # Not implemented — see llm_prompts.<key>.model

  geo_correlation:
    enabled: true                           # Not implemented — correlation always runs
    time_offset: !duration 0 seconds        # Not implemented — use calibration.yaml instead
    max_time_diff: !duration 300 seconds    # Maximum correlation window

  poi_detection:
    enabled: false                          # Enable POI detection (requires PostgreSQL+PostGIS)
    connection:
      host: localhost                       # PostgreSQL host
      database: mkmapdiary                  # Database name
      user: mkmapdiary                      # Database user
      password: null                        # Database password (null for no password)
    max_age: !duration 300 days             # Not implemented
    priorities:                             # Symbol priority (higher = more important, null = disabled)
      city: 100
      town: 90
      village: 80
      train_station: 30

  iqa:
    enabled: true                           # Image quality assessment
    method: !auto                           # clipiqa when torch/torchvision/piq are installed, else simple
    threshold: 0.1                          # For the clipiqa method
    stddev_factor: 2                        # For the simple method

  entropy_filtering:
    enabled: true                           # Flag low-entropy (near-empty) images
    threshold: 6.5                          # Not implemented

  image_comparison:
    enabled: true                           # Perceptual-hash duplicate detection

  track_simplification:
    enabled: true
    tolerance: !distance 1 meter            # Set to 0 to disable simplification
```

**Not implemented:** the keys marked above are accepted by the schema but no code reads
them yet. They are listed here because they appear in `defaults.yaml`; do not rely on
them. In particular, per-camera clock offsets are configured through
[`calibration.yaml`](calibration.md), not through `features.geo_correlation.time_offset`.

**Note:** POI detection is disabled by default and requires PostgreSQL with PostGIS. See [How to Set Up POI Detection](../how-to_guides/setup-poi-detection.md) for detailed setup instructions.

### Site Section

Controls website generation and appearance.

```yaml
site:
  image_format: jpg                         # Output image format (jpg, png, webp)
  image_options: {}                         # PIL/Pillow save options
  locale: !auto                             # Auto-detect or locale string
  timezone: !auto                           # Auto-detect or timezone string
```

### Debug Section

```yaml
debug:
  enable_user_cache: false                  # Keep expensive intermediate results in the user cache
```

### Ignore Dates

Dates listed here are skipped entirely — no day page and no GPX file is generated for
them. YAML parses the entries as dates, so write them unquoted in `yyyy-mm-dd` form.

```yaml
ignore_dates:
  - 2026-08-01
  - 2026-08-04
```

### Strings Section

Override the translated text used in the generated site. Every key defaults to `null`,
meaning "use the translation for the site locale". The set of keys is fixed by the
schema and covers page titles, map legend labels, gallery quality labels, track
statistics, credits headings, the AI disclosure, and the LLM prompt texts:

```yaml
strings:
  site_name: "My Adventure Journal"
  journal_title: null                       # null = use the default translation
  map_title: null
  days_title: null
  audio_title: null
  text_title: null
  gallery_title: null
  home_title: null
  # ... plus legend_*, quality_*, track_*, credits_*, ai_disclosure_* and the
  # *_prompt keys; see resources/defaults.yaml for the complete list
```

The `*_prompt` keys (`generate_title_prompt`, `generate_tags_prompt`,
`summarize_journal_entry_prompt`, `summarize_image_prompt`,
`assess_image_quality_prompt`) hold the LLM prompt texts. Prompts are translations like
any other string, so overriding a prompt means overriding its string here — see below.

### LLM Prompts Section

Selects the model and inference options per prompt. The prompt *text* is not stored
here: `translation_key` points at an entry in the `strings` section, which
[`BaseTask.ai()`](https://github.com/bytehexe/mkmapdiary/blob/main/src/mkmapdiary/tasks/base/baseTask.py)
formats before calling ollama.

```yaml
llm_prompts:
  generate_title:
    translation_key: generate_title_prompt  # Which strings.* entry holds the prompt
    model: "granite3.3:8b"                  # ollama model for this prompt
    options:
      temperature: 0.2                      # Any ollama option; passed through as-is
      # seed: 42                            # Optional: random seed for reproducibility

  generate_tags:
    translation_key: generate_tags_prompt
    model: "granite3.3:8b"
    options:
      temperature: 0.8
```

The five configurable prompts are `generate_title`, `generate_tags`,
`summarize_journal_entry`, `summarize_image` and `assess_image_quality`. Only the first
three are reached by a build today: `summarize_image` belongs to the ImageSummarizer
postprocessor, which is disabled, and nothing calls `assess_image_quality` — image
quality is scored by CLIP-IQA or a statistical heuristic, not by a language model. The schema also
accepts a literal `prompt:` key here, but nothing reads it — the prompt text always comes
from `translation_key`.

To replace a prompt's text, override its string. `{text}` and `{locale}` are substituted
before the prompt is sent:

```yaml
strings:
  generate_title_prompt: |
    Create exactly one title that summarizes the following text in {locale}.
    The title must be a single phrase, 3–5 words long.
    Output only the title, nothing else.

    Text:
    {text}
```

### Credits Section

Names shown on the generated credits page, alongside the dependency and
frontend-library credits computed automatically at build time.

```yaml
credits:
  travellers:                              # Names shown on the credits page
    - Janna Hopp
    - Alex
  creators:                                # General credit for the media
    - Bob Ross
```

`credits.creators` is a general credit for the media. It is merged and
deduplicated with the creators picked up automatically from `calibration.yaml`
files and from EXIF metadata, and shown only on the credits page — never on an
individual asset.

## Special Tags

### !auto Tag

The `!auto` tag enables automatic detection of system values. It takes no argument — the
key it is written under decides what is detected:

- `site.locale` - Use the system locale
- `site.timezone` - Use the system timezone
- `features.transcription.enabled` - True when `whisper` is installed
- `features.iqa.method` - `clipiqa` when `torch`, `torchvision` and `piq` are installed,
  otherwise `simple`

Using `!auto` under any other key is an error.

### !duration Tag

The `!duration` tag converts human-readable durations to seconds:

- `!duration 0 seconds`
- `!duration 5 minutes`
- `!duration 2 hours`
- `!duration 300 days`

### !distance Tag

The `!distance` tag converts human-readable distances to meters:

- `!distance 1 meter`
- `!distance 250 cm`
- `!distance 0.5 km`

## Command-Line Configuration

Override any configuration value using the `-x` flag, accepted by both `build` and
`config`. The key uses dot notation for nested keys, and the value is everything
after the first `=`:

```bash
# Enable/disable features
mkmapdiary build -x features.transcription.enabled=true source_dir
mkmapdiary build -x features.llms.enabled=false source_dir

# Set the model used for one prompt
mkmapdiary build -x llm_prompts.generate_title.model="granite3.3:8b" source_dir

# Configure timing
mkmapdiary build -x features.geo_correlation.max_time_diff="!duration 10 minutes" source_dir

# Set site options
mkmapdiary build -x site.image_format=png source_dir
mkmapdiary build -x strings.site_name="My Travel Journal" source_dir
```

### Parameter Values Are YAML

The value is parsed as YAML, not taken as a string, so every type the configuration
files support can be given on the command line — including the
[special tags](#special-tags):

| Example | Resulting value |
| --- | --- |
| `-x site.image_format=webp` | the string `webp` |
| `-x features.llms.enabled=no` | the boolean `false` |
| `-x features.poi_detection.connection.password=null` | `null` |
| `-x 'credits.travellers=["Ada", "Bob"]'` | a list of two strings |
| `-x 'site.image_options={quality: 80, optimize: true}'` | a mapping |
| `-x 'ignore_dates=[2020-01-01]'` | a list of one date |
| `-x 'features.geo_correlation.max_time_diff=!duration 5 minutes'` | `300` |
| `-x 'features.track_simplification.tolerance=!distance 2.5 km'` | `2500.0` |
| `-x site.locale=!auto` | the detected locale |

Two consequences worth knowing:

- **Quote the value in the shell** whenever it contains spaces, brackets, braces or a
  `!`. Otherwise the shell, not mkmapdiary, decides what arrives.
- **YAML booleans are broad.** `no`, `off` and `n` all mean `false`, so
  `-x strings.site_name=No` passes a boolean where a string was meant and fails with
  the puzzling `False is not valid under any of the given schemas`. Quote it inside
  the value — `-x 'strings.site_name="No"'` — to keep it a string.

Each parameter is validated against the schema on its own, so overriding a key with a
value of the wrong shape fails immediately rather than at build time:

```console
$ mkmapdiary config --get -x features.transcription=False source_dir
ERROR 💥 Config parameter 'features.transcription=False' is invalid: False is not of type 'object'
      Path: features.transcription
```

Use `mkmapdiary config --get` to check what a parameter actually resolves to before
committing to it.

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

### Effective Configuration

To see the result of all the layers combined — defaults, user configuration,
project configuration and `-x` parameters — without writing anything:

```bash
mkmapdiary config --get source_dir
```

See [the `config` command](commands.md#showing-the-effective-configuration)
for details.

## Examples

### Basic Configuration

```yaml
features:
  llms:
    enabled: true
  geo_correlation:
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
  geo_correlation:
    max_time_diff: !duration 10 minutes
  poi_detection:
    enabled: true
    connection:
      host: localhost
      database: mkmapdiary
      user: mkmapdiary
      password: my_secure_password
    priorities:
      city: 100
      town: 90
      village: 80
      train_station: null      # Do not show train stations
  iqa:
    enabled: true
    method: clipiqa
    threshold: 0.15
  track_simplification:
    tolerance: !distance 2 meters

site:
  image_format: jpg
  image_options:
    quality: 85
    optimize: true
  locale: "de_DE.UTF-8"
  timezone: "Europe/Berlin"

ignore_dates:
  - 2026-08-04          # Travel day, nothing worth a page

credits:
  travellers:
    - Janna Hopp

strings:
  site_name: "Reisetagebuch"
  journal_title: "Tagebuch"
  map_title: "Karte"
  generate_title_prompt: |
    Erstelle genau einen Titel, der den folgenden Text auf Deutsch zusammenfasst.
    Der Titel muss eine einzige Phrase sein, 3-5 Wörter lang.

    Text:
    {text}

llm_prompts:
  generate_title:
    model: "granite3.3:8b"
    options:
      temperature: 0.1
```