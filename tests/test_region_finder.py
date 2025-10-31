import json
import pathlib

import pytest
import requests
import shapely

from mkmapdiary.poi.regionFinder import RegionFinder


def load_geofabrik_data():
    # Load geofabrik data
    pathlib.Path(".test-cache").mkdir(parents=True, exist_ok=True)
    index_path = pathlib.Path(".test-cache") / "geofabrik_index.json"
    if index_path.exists():
        with open(index_path) as f:
            geofabrik_data = json.load(f)
    else:
        response = requests.get("https://download.geofabrik.de/index-v1.json")
        geofabrik_data = response.json()
        with open(index_path, "w") as f:
            json.dump(geofabrik_data, f)
    return geofabrik_data


@pytest.mark.local
def test_find_best_region_internal():
    # This test can be implemented to test the internal _findBestRegion method
    geofabrik_data = load_geofabrik_data()

    geo_data_list = [
        # Define some test geo_data here, e.g., as shapely geometries
        # Point: Berlin
        [shapely.Point(13.4050, 52.5200), ["berlin"]],
        # Point: Paris
        [shapely.Point(2.3522, 48.8566), ["ile-de-france"]],
    ]
    for geo_data, expected_region_ids in geo_data_list:
        finder = RegionFinder(geo_data, geofabrik_data)
        best_region, _ = finder._findBestRegion(geo_data, [])
        region_ids = [best_region.id] if best_region else []
        assert region_ids == expected_region_ids


@pytest.mark.local
def test_find_regions_with_cache():
    geofabrik_data = load_geofabrik_data()

    geo_data_list = [
        # Define some test geo_data here, e.g., as shapely geometries
        # Point: Berlin
        [shapely.Point(13.4050, 52.5200), ["berlin"]],
        # Two points: Berlin and Potsdam
        [
            shapely.MultiPoint([(13.4050, 52.5200), (13.0583, 52.3906)]),
            ["berlin", "brandenburg"],
        ],
    ]
    for geo_data, expected_region_ids in geo_data_list:
        finder = RegionFinder(geo_data, geofabrik_data)
        regions = finder.find_regions()
        region_ids = [region.id for region in regions]
        assert region_ids == expected_region_ids
