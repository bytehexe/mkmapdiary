import pathlib

import numpy as np
import pytest
import whenever

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.lib.startPage import StartPage


class TestStartPageTimeDistanceMatrix:
    """Test the time distance matrix calculation method in StartPage."""

    def test_calculate_time_distance_matrix_empty_assets(self) -> None:
        """Test time distance matrix calculation with empty asset list."""
        result = StartPage._calculate_time_distance_matrix([])
        assert result.shape == (0, 0)

    def test_calculate_time_distance_matrix_single_asset(self) -> None:
        """Test time distance matrix calculation with single asset."""
        asset = AssetRecord(
            path=pathlib.Path("/test.jpg"),
            type="image",
            timestamp_utc=whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0),
        )

        result = StartPage._calculate_time_distance_matrix([asset])

        # Single asset should result in 1x1 matrix with value 0
        assert result.shape == (1, 1)
        assert result[0, 0] == 0.0

    def test_calculate_time_distance_matrix_two_assets(self) -> None:
        """Test time distance matrix calculation with two assets."""
        asset1 = AssetRecord(
            path=pathlib.Path("/test1.jpg"),
            type="image",
            timestamp_utc=whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0),  # noon
        )
        asset2 = AssetRecord(
            path=pathlib.Path("/test2.jpg"),
            type="image",
            timestamp_utc=whenever.Instant.from_utc(
                2023, 1, 1, 13, 0, 0
            ),  # 1 PM (1 hour later)
        )

        result = StartPage._calculate_time_distance_matrix([asset1, asset2])

        # Should be 2x2 symmetric matrix
        assert result.shape == (2, 2)

        # Diagonal should be 0
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0

        # Matrix should be symmetric
        assert result[0, 1] == result[1, 0]

        # Values should be normalized to [0, 1] range
        assert 0.0 <= result[0, 1] <= 1.0

    def test_calculate_time_distance_matrix_multiple_assets(self) -> None:
        """Test time distance matrix calculation with multiple assets."""
        base_time = whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0)
        assets = []

        for i in range(5):
            # Assets spaced 30 minutes apart
            timestamp = base_time + whenever.TimeDelta(minutes=30 * i)
            asset = AssetRecord(
                path=pathlib.Path(f"/test{i}.jpg"),
                type="image",
                timestamp_utc=timestamp,
            )
            assets.append(asset)

        result = StartPage._calculate_time_distance_matrix(assets)

        # Should be 5x5 symmetric matrix
        assert result.shape == (5, 5)

        # Diagonal should be all zeros
        for i in range(5):
            assert result[i, i] == 0.0

        # Matrix should be symmetric
        for i in range(5):
            for j in range(5):
                assert result[i, j] == result[j, i]

        # Values should be normalized to [0, 1] range
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)

        # Distance should increase with time difference
        # Asset 0 to Asset 1 should be less than Asset 0 to Asset 4
        assert result[0, 1] < result[0, 4]

    def test_calculate_time_distance_matrix_same_timestamp(self) -> None:
        """Test time distance matrix calculation with assets having same timestamp."""
        timestamp = whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0)

        assets = []
        for i in range(3):
            asset = AssetRecord(
                path=pathlib.Path(f"/test{i}.jpg"),
                type="image",
                timestamp_utc=timestamp,  # Same timestamp for all
            )
            assets.append(asset)

        result = StartPage._calculate_time_distance_matrix(assets)

        # Should be 3x3 matrix with all zeros (same timestamps)
        assert result.shape == (3, 3)
        assert np.allclose(result, np.zeros((3, 3)))

    def test_calculate_time_distance_matrix_none_timestamp_assertion(self) -> None:
        """Test that None timestamps cause assertion error."""
        asset1 = AssetRecord(
            path=pathlib.Path("/test1.jpg"),
            type="image",
            timestamp_utc=None,  # None timestamp should cause assertion
        )
        asset2 = AssetRecord(
            path=pathlib.Path("/test2.jpg"),
            type="image",
            timestamp_utc=whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0),
        )

        # Should raise AssertionError for None timestamp when comparing assets
        with pytest.raises(AssertionError):
            StartPage._calculate_time_distance_matrix([asset1, asset2])

    def test_calculate_time_distance_matrix_extreme_time_differences(self) -> None:
        """Test time distance matrix with extreme time differences."""
        asset1 = AssetRecord(
            path=pathlib.Path("/test1.jpg"),
            type="image",
            timestamp_utc=whenever.Instant.from_utc(2020, 1, 1, 0, 0, 0),
        )
        asset2 = AssetRecord(
            path=pathlib.Path("/test2.jpg"),
            type="image",
            timestamp_utc=whenever.Instant.from_utc(2023, 12, 31, 23, 59, 59),
        )

        result = StartPage._calculate_time_distance_matrix([asset1, asset2])

        # Should handle extreme differences properly
        assert result.shape == (2, 2)
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0
        assert result[0, 1] == result[1, 0]

        # With normalization, the max difference should be 1.0
        assert result[0, 1] == 1.0

    def test_calculate_time_distance_matrix_millisecond_precision(self) -> None:
        """Test time distance matrix with millisecond-level differences."""
        base_time = whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0)

        # Create assets with very small time differences
        asset1 = AssetRecord(
            path=pathlib.Path("/test1.jpg"), type="image", timestamp_utc=base_time
        )
        asset2 = AssetRecord(
            path=pathlib.Path("/test2.jpg"),
            type="image",
            timestamp_utc=base_time + whenever.TimeDelta(milliseconds=100),
        )
        asset3 = AssetRecord(
            path=pathlib.Path("/test3.jpg"),
            type="image",
            timestamp_utc=base_time + whenever.TimeDelta(milliseconds=200),
        )

        result = StartPage._calculate_time_distance_matrix([asset1, asset2, asset3])

        # Should be 3x3 matrix
        assert result.shape == (3, 3)

        # Diagonal should be zeros
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0
        assert result[2, 2] == 0.0

        # Should be symmetric (with floating point tolerance)
        assert np.isclose(result[0, 1], result[1, 0])
        assert np.isclose(result[0, 2], result[2, 0])
        assert np.isclose(result[1, 2], result[2, 1])

        # Values should be normalized
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)

    def test_calculate_time_distance_matrix_normalization_properties(self) -> None:
        """Test that normalization preserves relative distances."""
        base_time = whenever.Instant.from_utc(2023, 1, 1, 12, 0, 0)

        assets = [
            AssetRecord(
                path=pathlib.Path("/test1.jpg"), type="image", timestamp_utc=base_time
            ),
            AssetRecord(
                path=pathlib.Path("/test2.jpg"),
                type="image",
                timestamp_utc=base_time + whenever.TimeDelta(minutes=10),
            ),
            AssetRecord(
                path=pathlib.Path("/test3.jpg"),
                type="image",
                timestamp_utc=base_time + whenever.TimeDelta(minutes=20),
            ),
            AssetRecord(
                path=pathlib.Path("/test4.jpg"),
                type="image",
                timestamp_utc=base_time + whenever.TimeDelta(minutes=30),
            ),
        ]

        result = StartPage._calculate_time_distance_matrix(assets)

        # Should be 4x4 matrix
        assert result.shape == (4, 4)

        # Maximum distance should be 1.0 (between assets 0 and 3)
        assert result[0, 3] == 1.0
        assert result[3, 0] == 1.0

        # Relative distances should be preserved
        # Distance 0->1 should be 1/3 of distance 0->3
        expected_ratio = result[0, 1] / result[0, 3]
        assert abs(expected_ratio - 1 / 3) < 0.01

        # Distance 0->2 should be 2/3 of distance 0->3
        expected_ratio = result[0, 2] / result[0, 3]
        assert abs(expected_ratio - 2 / 3) < 0.01


class TestStartPageGeoDistanceMatrix:
    """Test the geographic distance matrix calculation method in StartPage."""

    def test_calculate_geo_distance_matrix_empty_assets(self) -> None:
        """Test geo distance matrix calculation with empty asset list."""
        result = StartPage._calculate_geo_distance_matrix([])
        # Empty input should return 0x0 matrix
        assert result.shape == (0, 0)

    def test_calculate_geo_distance_matrix_single_asset(self) -> None:
        """Test geo distance matrix calculation with single asset."""
        asset = AssetRecord(
            path=pathlib.Path("/test.jpg"),
            type="image",
            latitude=52.520008,  # Berlin
            longitude=13.404954,
        )

        result = StartPage._calculate_geo_distance_matrix([asset])

        # Single asset should result in 1x1 matrix with value 0
        assert result.shape == (1, 1)
        assert result[0, 0] == 0.0

    def test_calculate_geo_distance_matrix_two_cities(self) -> None:
        """Test geo distance matrix calculation between two well-known cities."""
        # Berlin and Paris coordinates
        asset_berlin = AssetRecord(
            path=pathlib.Path("/berlin.jpg"),
            type="image",
            latitude=52.520008,
            longitude=13.404954,
        )
        asset_paris = AssetRecord(
            path=pathlib.Path("/paris.jpg"),
            type="image",
            latitude=48.858844,
            longitude=2.294351,
        )

        result = StartPage._calculate_geo_distance_matrix([asset_berlin, asset_paris])

        # Should be 2x2 symmetric matrix
        assert result.shape == (2, 2)

        # Diagonal should be 0
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0

        # Matrix should be symmetric
        assert np.isclose(result[0, 1], result[1, 0])

        # Values should be normalized to [0, 1] range
        assert 0.0 <= result[0, 1] <= 1.0

        # Since there are only two points, the distance should be 1.0 after normalization
        assert result[0, 1] == 1.0

    def test_calculate_geo_distance_matrix_multiple_cities(self) -> None:
        """Test geo distance matrix with multiple European cities."""
        assets = [
            AssetRecord(
                path=pathlib.Path("/berlin.jpg"),
                type="image",
                latitude=52.520008,  # Berlin
                longitude=13.404954,
            ),
            AssetRecord(
                path=pathlib.Path("/paris.jpg"),
                type="image",
                latitude=48.858844,  # Paris
                longitude=2.294351,
            ),
            AssetRecord(
                path=pathlib.Path("/london.jpg"),
                type="image",
                latitude=51.507351,  # London
                longitude=-0.127758,
            ),
            AssetRecord(
                path=pathlib.Path("/madrid.jpg"),
                type="image",
                latitude=40.416775,  # Madrid
                longitude=-3.703790,
            ),
        ]

        result = StartPage._calculate_geo_distance_matrix(assets)

        # Should be 4x4 symmetric matrix
        assert result.shape == (4, 4)

        # Diagonal should be all zeros
        for i in range(4):
            assert result[i, i] == 0.0

        # Matrix should be symmetric
        for i in range(4):
            for j in range(4):
                assert np.isclose(result[i, j], result[j, i])

        # Values should be normalized to [0, 1] range
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)

        # The maximum distance should be 1.0 (normalized)
        assert np.max(result) == 1.0

    def test_calculate_geo_distance_matrix_close_coordinates(self) -> None:
        """Test geo distance matrix with very close coordinates."""
        # Three points within Berlin (very close to each other)
        assets = [
            AssetRecord(
                path=pathlib.Path("/berlin1.jpg"),
                type="image",
                latitude=52.520008,  # Brandenburg Gate
                longitude=13.404954,
            ),
            AssetRecord(
                path=pathlib.Path("/berlin2.jpg"),
                type="image",
                latitude=52.518623,  # Potsdamer Platz (about 200m away)
                longitude=13.408070,
            ),
            AssetRecord(
                path=pathlib.Path("/berlin3.jpg"),
                type="image",
                latitude=52.516275,  # Checkpoint Charlie (about 500m away)
                longitude=13.390140,
            ),
        ]

        result = StartPage._calculate_geo_distance_matrix(assets)

        # Should be 3x3 matrix
        assert result.shape == (3, 3)

        # Diagonal should be zeros
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0
        assert result[2, 2] == 0.0

        # Should be symmetric
        assert np.isclose(result[0, 1], result[1, 0])
        assert np.isclose(result[0, 2], result[2, 0])
        assert np.isclose(result[1, 2], result[2, 1])

        # Values should be normalized
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)

    def test_calculate_geo_distance_matrix_same_coordinates(self) -> None:
        """Test geo distance matrix with identical coordinates."""
        # All assets at the same location
        coords = (52.520008, 13.404954)  # Berlin
        assets = []
        for i in range(3):
            asset = AssetRecord(
                path=pathlib.Path(f"/same_location_{i}.jpg"),
                type="image",
                latitude=coords[0],
                longitude=coords[1],
            )
            assets.append(asset)

        result = StartPage._calculate_geo_distance_matrix(assets)

        # Should be 3x3 matrix with all zeros
        assert result.shape == (3, 3)
        assert np.allclose(result, np.zeros((3, 3)))

    def test_calculate_geo_distance_matrix_antipodes(self) -> None:
        """Test geo distance matrix with points on opposite sides of Earth."""
        assets = [
            AssetRecord(
                path=pathlib.Path("/madrid.jpg"),
                type="image",
                latitude=40.416775,  # Madrid, Spain
                longitude=-3.703790,
            ),
            AssetRecord(
                path=pathlib.Path("/wellington.jpg"),
                type="image",
                latitude=-41.276825,  # Wellington, New Zealand (approximately antipodal)
                longitude=174.777969,
            ),
        ]

        result = StartPage._calculate_geo_distance_matrix(assets)

        # Should be 2x2 matrix
        assert result.shape == (2, 2)

        # Diagonal should be zeros
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0

        # Should be symmetric
        assert np.isclose(result[0, 1], result[1, 0])

        # Maximum distance should be 1.0 (normalized)
        assert result[0, 1] == 1.0

    def test_calculate_geo_distance_matrix_polar_regions(self) -> None:
        """Test geo distance matrix with extreme latitude coordinates."""
        assets = [
            AssetRecord(
                path=pathlib.Path("/north_pole.jpg"),
                type="image",
                latitude=89.0,  # Near North Pole
                longitude=0.0,
            ),
            AssetRecord(
                path=pathlib.Path("/south_pole.jpg"),
                type="image",
                latitude=-89.0,  # Near South Pole
                longitude=0.0,
            ),
            AssetRecord(
                path=pathlib.Path("/equator.jpg"),
                type="image",
                latitude=0.0,  # Equator
                longitude=0.0,
            ),
        ]

        result = StartPage._calculate_geo_distance_matrix(assets)

        # Should be 3x3 matrix
        assert result.shape == (3, 3)

        # Should handle extreme coordinates properly
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)

        # Diagonal should be zeros
        for i in range(3):
            assert result[i, i] == 0.0

        # Should be symmetric
        for i in range(3):
            for j in range(3):
                assert np.isclose(result[i, j], result[j, i])

    def test_calculate_geo_distance_matrix_none_coordinates_assertion(self) -> None:
        """Test that None coordinates cause an error."""
        asset_valid = AssetRecord(
            path=pathlib.Path("/valid.jpg"),
            type="image",
            latitude=52.520008,
            longitude=13.404954,
        )
        asset_invalid = AssetRecord(
            path=pathlib.Path("/invalid.jpg"),
            type="image",
            latitude=None,  # Invalid coordinate
            longitude=13.404954,
        )

        # Should raise an AssertionError when coordinates are None
        with pytest.raises(AssertionError):
            StartPage._calculate_geo_distance_matrix([asset_valid, asset_invalid])

    def test_calculate_geo_distance_matrix_distance_ordering(self) -> None:
        """Test that geographic distances are ordered correctly."""
        # Create a line of cities from west to east
        assets = [
            AssetRecord(
                path=pathlib.Path("/lisbon.jpg"),
                type="image",
                latitude=38.722252,  # Lisbon, Portugal
                longitude=-9.139337,
            ),
            AssetRecord(
                path=pathlib.Path("/madrid.jpg"),
                type="image",
                latitude=40.416775,  # Madrid, Spain
                longitude=-3.703790,
            ),
            AssetRecord(
                path=pathlib.Path("/paris.jpg"),
                type="image",
                latitude=48.858844,  # Paris, France
                longitude=2.294351,
            ),
            AssetRecord(
                path=pathlib.Path("/berlin.jpg"),
                type="image",
                latitude=52.520008,  # Berlin, Germany
                longitude=13.404954,
            ),
        ]

        result = StartPage._calculate_geo_distance_matrix(assets)

        # Should be 4x4 matrix
        assert result.shape == (4, 4)

        # Distance from Lisbon to Madrid should be less than Lisbon to Berlin
        assert result[0, 1] < result[0, 3]

        # Distance from Madrid to Paris should be less than Madrid to Berlin
        assert result[1, 2] < result[1, 3]

        # Adjacent cities should have smaller distances than distant ones
        assert result[0, 1] < result[0, 2]  # Lisbon-Madrid < Lisbon-Paris
        assert result[1, 2] < result[1, 3]  # Madrid-Paris < Madrid-Berlin
        assert result[2, 3] < result[2, 0]  # Paris-Berlin < Paris-Lisbon
