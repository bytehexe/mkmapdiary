# How to Set Up POI Detection

This guide walks you through setting up the POI (Points of Interest) detection feature in mkmapdiary. This feature automatically identifies and displays nearby landmarks, cities, and other notable locations on your travel maps.

## Overview

POI detection uses OpenStreetMap data to enrich your travel journal with contextual information about places you've visited. The feature requires a PostgreSQL database with the PostGIS extension to store and query geographic data efficiently.

## Prerequisites

Before you begin, you'll need:

- PostgreSQL (version 12 or higher recommended)
- PostGIS extension for PostgreSQL
- Administrator/sudo access to install packages and create databases

## Step 1: Install PostgreSQL and PostGIS

Choose the instructions for your operating system:

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install postgresql postgis
```

The PostgreSQL service should start automatically after installation.

### macOS

```bash
brew install postgresql@16 postgis
brew services start postgresql@16
```

### Arch Linux

```bash
sudo pacman -S postgresql postgis
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl start postgresql
```

## Step 2: Create Database and User

Create a dedicated database and user for mkmapdiary:

```bash
# Create user (you'll be prompted to enter a password)
sudo -u postgres createuser -P mkmapdiary

# Create database owned by the mkmapdiary user
sudo -u postgres createdb -O mkmapdiary mkmapdiary

# Enable PostGIS extension
sudo -u postgres psql -d mkmapdiary -c "CREATE EXTENSION postgis;"
```

### Verify Installation

Check that everything is set up correctly:

```bash
# Connect to the database
sudo -u postgres psql -d mkmapdiary

# Check PostGIS version (inside psql)
SELECT PostGIS_Version();

# Exit psql
\q
```

## Step 3: Configure mkmapdiary

Create or edit your configuration file to store your database credentials securely:

- **Project-specific:** `config.yaml` in your source directory
- **User-wide:** `~/.config/mkmapdiary/config.yaml`

```yaml
features:
  poi_detection:
    enabled: true
    connection:
      host: localhost
      database: mkmapdiary
      user: mkmapdiary
      password: your_password_here
    max_age: !duration 300 days
    priorities:
      city: 100
      town: 90
      village: 80
      train_station: 30
```

**Security Best Practices:**

- Store passwords in configuration files, not on the command line
- Use file permissions to protect your config file: `chmod 600 config.yaml`
- Never commit configuration files with passwords to version control

**Configuration Options:**

- **`enabled`**: Set to `true` to enable POI detection
- **`connection.host`**: PostgreSQL server hostname (typically `localhost`)
- **`connection.database`**: Database name (should match the database created in Step 2)
- **`connection.user`**: Database username (should match the user created in Step 2)
- **`connection.password`**: Database password
- **`max_age`**: Maximum age for cached POI data before rebuilding indexes
- **`priorities`**: Priority values for different POI types (higher values = more important; `null` to disable a type)

### Alternative: Command-Line Configuration

You can enable POI detection via command-line parameters for some options:

```bash
mkmapdiary build \
  -x features.poi_detection.enabled=true \
  source_dir
```

**Security Note:** Never pass passwords via command-line arguments as they may be visible in shell history and process lists. Always use a configuration file for sensitive credentials.

## Step 4: Test POI Detection

Run mkmapdiary on a directory containing GPS tracks:

```bash
mkmapdiary build source_dir
```

On the first run with POI detection enabled, mkmapdiary will:

1. Download OpenStreetMap data for the regions covered by your GPS tracks
2. Build spatial indexes for efficient POI queries
3. Cache the indexes in `~/.mkmapdiary/cache/poi_index/`

This initial setup may take several minutes depending on the size of the regions. Subsequent builds will use the cached indexes and be much faster.

## Troubleshooting

### Database Connection Issues

**Error: "could not connect to server"**

- Check that PostgreSQL is running: `sudo systemctl status postgresql`
- Verify the host and port in your configuration
- Check PostgreSQL logs: `sudo journalctl -u postgresql`

**Error: "password authentication failed"**

- Verify the username and password in your configuration
- Check PostgreSQL authentication settings in `/etc/postgresql/*/main/pg_hba.conf`

### PostGIS Extension Issues

**Error: "extension postgis does not exist"**

Make sure PostGIS is installed and the extension is created:

```bash
sudo apt install postgis  # or your package manager
sudo -u postgres psql -d mkmapdiary -c "CREATE EXTENSION postgis;"
```

### Permission Issues

**Error: "permission denied for database"**

Ensure the user has proper permissions:

```bash
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mkmapdiary TO mkmapdiary;"
```

## Advanced Configuration

### Custom Priority Settings

You can customize which POI types to include and their importance levels. Higher priority POIs are shown at lower zoom levels. See the default priorities in [`defaults.yaml`](https://github.com/bytehexe/mkmapdiary/blob/main/src/mkmapdiary/resources/defaults.yaml).

To disable a specific POI type, set its priority to `null`:

```yaml
features:
  poi_detection:
    priorities:
      city: 100
      town: 90
      village: 80
      train_station: null  # Disable train stations
```

### Using a Remote Database

If your PostgreSQL database is on a different server:

```yaml
features:
  poi_detection:
    connection:
      host: db.example.com
      database: mkmapdiary
      user: mkmapdiary
      password: your_password
```

## Next Steps

- Learn about [POI index format](../reference/poi-index-format.md)
- Customize [POI filter configuration](../reference/poi-index-format.md#filter-configuration-integration)
- Explore other [configuration options](../reference/configuration.md)
