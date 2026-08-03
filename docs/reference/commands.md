# Command Reference

mkmapdiary uses a command-based interface with five subcommands: `build`, `config`,
`generate-demo`, `calibrate`, and `inspect`.

## Global Options

These options are available for all commands:

```bash
mkmapdiary [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Verbosity Options

- `-v, --verbose`: Increase verbosity level. Can be used multiple times (`-vv` for even more verbose)
- `-q, --quiet`: Decrease verbosity level. Can be used multiple times

Examples:
```bash
mkmapdiary -v build source_dir        # Verbose build
mkmapdiary -q config --user           # Quiet config update
mkmapdiary -vv build source_dir       # Very verbose build
```

## build

Build a travel journal from source directory to distribution directory.

```bash
mkmapdiary build [OPTIONS] SOURCE_DIR [DIST_DIR]
```

### Arguments

- `SOURCE_DIR`: Directory containing your travel data (GPS tracks, photos, notes)
- `DIST_DIR`: Output directory for the generated website (optional, defaults to `SOURCE_DIR_dist`)

### Options

- `-x, --params TEXT`: Add configuration parameter. Format: `key=value`. Can be used multiple times.
- `-b, --build-dir PATH`: Path to build directory (implies `-B`)
- `-B, --persistent-build`: Use persistent build directory instead of temporary
- `-a, --always-execute`: Always execute tasks, even if up-to-date
- `-n, --num-processes INTEGER`: Number of parallel processes (default: CPU count)
- `--no-cache`: Disable cache in home directory

### Examples

```bash
# Basic build
mkmapdiary build my_travel_data

# Build with custom output directory
mkmapdiary build my_travel_data my_website

# Build with configuration overrides
mkmapdiary build -x site.title="My Trip" my_travel_data

# Verbose build with persistent build directory
mkmapdiary -v build -B my_travel_data
```

## config

Manage configuration files for mkmapdiary projects.

```bash
mkmapdiary config [OPTIONS] [SOURCE_DIR]
```

### Arguments

- `SOURCE_DIR`: Project directory (required unless using `--user`)

### Options

- `-x, --params TEXT`: Configuration parameter to set. Format: `key=value`. Can be used multiple times.
- `--user`: Write to user config file instead of project config file

### Examples

```bash
# Set project-specific configuration
mkmapdiary config -x features.transcription.enabled=true my_project

# Set multiple configuration values
mkmapdiary config -x site.title="My Trip" -x site.author="John Doe" my_project

# Set user-wide configuration (affects all projects)
mkmapdiary config --user -x features.llms.enabled=false
```

## generate-demo

Generate demo data in a directory for testing purposes.

```bash
mkmapdiary generate-demo SOURCE_DIR
```

### Arguments

- `SOURCE_DIR`: Directory where demo data will be generated (must be empty)

### Examples

```bash
# Generate demo data and build
mkmapdiary generate-demo demo
mkmapdiary build demo
```

Note: This command is primarily for testing and development purposes. The target directory must be empty.

## calibrate

Write a `calibration.yaml` into a source directory. Every subcommand edits one such
file, merging into it rather than replacing it, so the four can be used in any order on
the same directory. See [Calibration files](calibration.md) for what the resulting file
means and how it is inherited by subdirectories.

```bash
mkmapdiary calibrate SUBCOMMAND [OPTIONS]
```

All subcommands take `-o, --output PATH`, which may be either the directory to calibrate
or the `calibration.yaml` inside it. It is required everywhere except `calibrate file`,
which falls back to the directory holding the reference image. `calibrate file`,
`calibrate effects` and `calibrate creator` also take `-n, --dry-run` to print the
result without writing.

### calibrate file

Derive the camera offset from a photo of a clock, a phone screen, or any other
reference whose true time you know.

```bash
mkmapdiary calibrate file [OPTIONS] IMAGE REF_TIME
```

- `IMAGE`: a photo taken by the camera to calibrate
- `REF_TIME`: the true time at which it was taken
- `--camera-tz TEXT`: timezone of the camera's own clock (default: system localtime)
- `--ref-tz TEXT`: timezone `REF_TIME` is given in (default: system localtime)

### calibrate manual

Write a known offset directly, without a reference photo.

```bash
mkmapdiary calibrate manual -o PATH [-x SECONDS] [--camera-tz TEXT]
```

- `-x, --offset INTEGER`: offset in seconds; positive means the camera clock runs ahead

### calibrate effects

Manage the per-directory effects list. Currently only `autorotate` is supported.

```bash
mkmapdiary calibrate effects -o PATH [--add NAME] [--remove NAME]
```

`--add` and `--remove` may each be given multiple times.

### calibrate creator

Record who made the media in a directory. The name is shown next to each asset's time
and place — but only when the journal holds more than one distinct creator — and always
on the credits page.

```bash
mkmapdiary calibrate creator -o PATH [NAME]
mkmapdiary calibrate creator -o PATH --unset
```

- `NAME`: the creator to record; required unless `--unset` is given
- `--unset`: clear the creator for this directory. This writes an explicit `null`, which
  overrides a creator inherited from a parent directory. Omitting the key entirely would
  inherit it instead — see [Calibration files](calibration.md#inheritance).

For images, a creator set here wins over any `Artist` recorded in the file's own EXIF
metadata.

### Examples

```bash
# The camera clock was 259 seconds fast
mkmapdiary calibrate manual -o trip/day1 -x 259

# Derive the same offset from a photo of a clock reading 14:32:10
mkmapdiary calibrate file trip/day1/IMG_0001.jpg 2026-08-02T14:32:10 -o trip/day1

# Credit a directory, then exempt one subdirectory from that credit
mkmapdiary calibrate creator -o trip "Janna Hopp"
mkmapdiary calibrate creator -o trip/borrowed-camera --unset
```

## inspect

Print the timestamps mkmapdiary reads from a source directory, so a calibration can be
checked before a full build.

```bash
mkmapdiary inspect [--tz TEXT] SOURCE
```

- `SOURCE`: the source directory to inspect
- `--tz TEXT`: timezone to display the timestamps in

## Configuration Parameter Format

Configuration parameters use dot notation to specify nested values:

```bash
# Simple values
mkmapdiary build -x site.title="My Travel Journal" source_dir

# Nested values
mkmapdiary build -x features.transcription.enabled=true source_dir
mkmapdiary build -x features.llms.text_model="llama3:70b" source_dir

# Special types (durations, etc.)
mkmapdiary build -x features.geo_correlation.max_time_diff="!duration 10 minutes" source_dir
```

## Migration from v1.x

If you were using the old single-command interface:

```bash
# Old (v1.x)
mkmapdiary source_dir
mkmapdiary -x key=value source_dir
mkmapdiary --config -x key=value

# New (v2.x)
mkmapdiary build source_dir
mkmapdiary build -x key=value source_dir
mkmapdiary config -x key=value source_dir
```