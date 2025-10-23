# POI Index (.idx) Format

The POI index format is a binary file format used by mkmapdiary to store preprocessed points of interest (POI) data for efficient spatial queries. These files use the `.idx` extension and are stored in the user's cache directory.

## Overview

The `.idx` files are created from OpenStreetMap (OSM) data downloaded from Geofabrik regions. They contain spatially-organized POI data that enables fast radius-based and nearest-neighbor queries without requiring expensive real-time OSM processing.

## File Location

Index files are stored in:
```
~/.mkmapdiary/cache/poi_index/{region_id}.idx
```

Where `{region_id}` corresponds to the Geofabrik region identifier (e.g., `brandenburg.idx`, `berlin.idx`).

## Binary Format Structure

The `.idx` files use [MessagePack](https://msgpack.org/) serialization and consist of two main sections:

### 1. Header Section

The header is the first MessagePack object in the file and contains metadata:

```python
{
    "version": 1,                    # Format version number
    "filter_hash": "abc123...",      # Hash of the filter configuration used
    "build_time": 1634567890.123     # Unix timestamp when index was built
}
```

**Fields:**
- `version` (int): Format version, currently always `1`
- `filter_hash` (str): SHA-256 hash of the POI filter configuration used to build the index
- `build_time` (float): Unix timestamp indicating when the index was created

### 2. Data Section

The data section contains the actual POI index organized by rank levels:

```python
{
    rank_level: {
        "coords": [(lat1, lon1), (lat2, lon2), ...],
        "data": [
            (poi_id, poi_name, (filter_item_id, filter_expression_id), rank),
            ...
        ]
    }
    # for rank_level in range(MIN_RANK, MAX_RANK + 1)
}
```

**Structure:**
- **Outer dict**: Keys are rank levels (integers from `MIN_RANK` to `MAX_RANK`)
- **coords**: List of coordinate tuples `(latitude, longitude)` in WGS84
- **data**: List of POI metadata tuples containing:
  - `poi_id` (int): Original OSM node/way/relation ID
  - `poi_name` (str): Display name of the POI
  - `(filter_item_id, filter_expression_id)` (tuple): References to filter configuration
  - `rank` (int): Calculated importance rank of the POI

## Rank System

The rank system determines POI importance and visibility at different zoom levels:

- **Lower ranks** (e.g., 1-5): Highly important POIs (major cities, landmarks)
- **Higher ranks** (e.g., 15-20): Less important POIs (small shops, local features)
- **Rank calculation**: Based on OSM `place` tags and geometric area for ways/relations

## Index Validation

Index files are validated before use:

1. **Age check**: Files older than 1 year (31,536,000 seconds) are rebuilt
2. **Filter validation**: The `filter_hash` must match the current filter configuration
3. **Format validation**: Header must be readable and contain required fields

## Usage in Code

### Reading an Index File

```python
from mkmapdiary.poi.indexFileReader import IndexFileReader

reader = IndexFileReader("~/.mkmapdiary/cache/poi_index/brandenburg.idx")

# Check validity
if reader.is_up_to_date(31536000) and reader.is_valid(filter_config):
    data = reader.read()
    header = reader.header
```

### Writing an Index File

```python
from mkmapdiary.poi.indexFileWriter import IndexFileWriter

writer = IndexFileWriter("output.idx", filter_config)
writer.write(index_data)
```

## Performance Characteristics

- **File size**: Typically 1-50 MB per region depending on POI density
- **Load time**: Usually < 1 second for reading into memory
- **Query performance**: O(log n) for spatial queries using ball trees built from the index data
- **Memory usage**: Entire index loaded into RAM for fast access

## Filter Configuration Integration

The index format is tightly coupled with the POI filter configuration (`poi_filter_config.yaml`). When the filter configuration changes, all existing index files become invalid and must be rebuilt to ensure consistency.

The filter hash ensures that:
- Index files match the current filtering rules
- POI categories and expressions are correctly applied
- Stale indexes are automatically detected and rebuilt

## Maintenance

Index files are automatically managed:
- **Created**: When first needed for a geographic region
- **Validated**: On each use for age and filter compatibility  
- **Rebuilt**: When outdated, invalid, or missing
- **Cached**: Reused across multiple mkmapdiary runs for performance

This caching strategy balances data freshness with performance, avoiding expensive OSM processing while ensuring reasonably up-to-date POI information.