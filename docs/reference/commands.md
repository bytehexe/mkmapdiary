# Command Reference

mkmapdiary uses a command-based interface with three main subcommands: `build`, `config`, and `generate-demo`.

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