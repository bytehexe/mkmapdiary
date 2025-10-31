import math

import numpy as np
import pytest

from mkmapdiary.geoCluster import GeoCluster


class TestGeoClusterMathematicalFunctions:
    """Test the mathematical functions in GeoCluster."""

    def test_greatcircle_angle_same_point(self):
        """Test great circle angle between the same point."""
        lat1 = lon1 = lat2 = lon2 = math.radians(45.0)  # Convert to radians
        angle = GeoCluster._greatcircle_angle(lat1, lon1, lat2, lon2)
        assert abs(angle) < 1e-10  # Should be approximately 0

    def test_greatcircle_angle_antipodal_points(self):
        """Test great circle angle between antipodal points."""
        # Points on opposite sides of the earth
        lat1, lon1 = math.radians(0.0), math.radians(0.0)  # Equator, Prime Meridian
        lat2, lon2 = math.radians(0.0), math.radians(180.0)  # Equator, Antimeridian
        angle = GeoCluster._greatcircle_angle(lat1, lon1, lat2, lon2)
        assert abs(angle - math.pi) < 1e-10  # Should be π radians (180°)

    def test_greatcircle_angle_quarter_circle(self):
        """Test great circle angle for quarter circle distance."""
        # North Pole to Equator should be π/2 radians (90°)
        lat1, lon1 = math.radians(90.0), math.radians(0.0)  # North Pole
        lat2, lon2 = math.radians(0.0), math.radians(0.0)  # Equator
        angle = GeoCluster._greatcircle_angle(lat1, lon1, lat2, lon2)
        assert abs(angle - math.pi / 2) < 1e-10

    def test_greatcircle_angle_known_cities(self):
        """Test great circle angle between known cities."""
        # New York City (40.7128° N, 74.0060° W) to London (51.5074° N, 0.1278° W)
        # Expected great circle distance is approximately 5585 km
        # Angular distance ≈ 5585 km / 6371 km ≈ 0.876 radians ≈ 50.2°
        nyc_lat, nyc_lon = math.radians(40.7128), math.radians(-74.0060)
        london_lat, london_lon = math.radians(51.5074), math.radians(-0.1278)

        angle = GeoCluster._greatcircle_angle(nyc_lat, nyc_lon, london_lat, london_lon)

        # Convert to degrees for easier verification
        angle_deg = math.degrees(angle)
        assert 49.0 < angle_deg < 51.0  # Approximate expected range

    def test_greatcircle_angle_symmetry(self):
        """Test that great circle angle is symmetric."""
        lat1, lon1 = math.radians(40.0), math.radians(-74.0)
        lat2, lon2 = math.radians(51.0), math.radians(0.0)

        angle1 = GeoCluster._greatcircle_angle(lat1, lon1, lat2, lon2)
        angle2 = GeoCluster._greatcircle_angle(lat2, lon2, lat1, lon1)

        assert abs(angle1 - angle2) < 1e-10

    def test_greatcircle_midpoint_same_point(self):
        """Test midpoint calculation for the same point."""
        lat = lon = math.radians(45.0)
        mid_lat, mid_lon = GeoCluster._greatcircle_midpoint(lat, lon, lat, lon)

        assert abs(mid_lat - lat) < 1e-10
        assert abs(mid_lon - lon) < 1e-10

    @pytest.mark.skip("Needs investigation")
    def test_greatcircle_midpoint_antipodal_points(self):
        """Test midpoint of antipodal points."""
        # Midpoint of antipodal points on the equator
        lat1, lon1 = math.radians(0.0), math.radians(0.0)  # Equator, Prime Meridian
        lat2, lon2 = math.radians(0.0), math.radians(180.0)  # Equator, Antimeridian

        mid_lat, mid_lon = GeoCluster._greatcircle_midpoint(lat1, lon1, lat2, lon2)

        # Midpoint should be at one of the poles (North or South)
        assert abs(abs(mid_lat) - math.pi / 2) < 1e-10  # Should be ±π/2 (±90°)

    def test_greatcircle_midpoint_equator_points(self):
        """Test midpoint of points on the equator."""
        lat1, lon1 = math.radians(0.0), math.radians(0.0)  # Equator, Prime Meridian
        lat2, lon2 = math.radians(0.0), math.radians(90.0)  # Equator, 90° East

        mid_lat, mid_lon = GeoCluster._greatcircle_midpoint(lat1, lon1, lat2, lon2)

        # Midpoint should be on equator at 45° East
        assert abs(mid_lat) < 1e-10  # Should be on equator (0°)
        assert abs(mid_lon - math.radians(45.0)) < 1e-10  # Should be at 45°

    def test_greatcircle_midpoint_known_cities(self):
        """Test midpoint between known cities."""
        # New York City to London
        nyc_lat, nyc_lon = math.radians(40.7128), math.radians(-74.0060)
        london_lat, london_lon = math.radians(51.5074), math.radians(-0.1278)

        mid_lat, mid_lon = GeoCluster._greatcircle_midpoint(
            nyc_lat, nyc_lon, london_lat, london_lon
        )

        # Convert back to degrees for verification
        mid_lat_deg = math.degrees(mid_lat)
        mid_lon_deg = math.degrees(mid_lon)

        # Midpoint should be somewhere over the North Atlantic
        # Approximate expected: ~54°N, ~37°W
        assert 50.0 < mid_lat_deg < 60.0  # Reasonable latitude range
        assert -45.0 < mid_lon_deg < -30.0  # Reasonable longitude range

    def test_greatcircle_midpoint_symmetry(self):
        """Test that midpoint calculation is symmetric."""
        lat1, lon1 = math.radians(40.0), math.radians(-74.0)
        lat2, lon2 = math.radians(51.0), math.radians(0.0)

        mid1_lat, mid1_lon = GeoCluster._greatcircle_midpoint(lat1, lon1, lat2, lon2)
        mid2_lat, mid2_lon = GeoCluster._greatcircle_midpoint(lat2, lon2, lat1, lon1)

        assert abs(mid1_lat - mid2_lat) < 1e-10
        assert abs(mid1_lon - mid2_lon) < 1e-10

    def test_mathematical_consistency(self):
        """Test consistency between angle and midpoint calculations."""
        # For any two points, the angle from point1 to midpoint should be
        # half the angle from point1 to point2
        lat1, lon1 = math.radians(40.0), math.radians(-74.0)
        lat2, lon2 = math.radians(51.0), math.radians(0.0)

        # Calculate full angle
        full_angle = GeoCluster._greatcircle_angle(lat1, lon1, lat2, lon2)

        # Calculate midpoint
        mid_lat, mid_lon = GeoCluster._greatcircle_midpoint(lat1, lon1, lat2, lon2)

        # Calculate angle to midpoint
        half_angle = GeoCluster._greatcircle_angle(lat1, lon1, mid_lat, mid_lon)

        # Half angle should be approximately half of full angle
        assert abs(2 * half_angle - full_angle) < 1e-8

    def test_edge_case_poles(self):
        """Test behavior at the poles."""
        # North Pole
        north_lat, north_lon = math.radians(90.0), math.radians(0.0)
        equator_lat, equator_lon = math.radians(0.0), math.radians(0.0)

        angle = GeoCluster._greatcircle_angle(
            north_lat, north_lon, equator_lat, equator_lon
        )
        assert abs(angle - math.pi / 2) < 1e-10  # Should be 90°

        # South Pole
        south_lat, south_lon = math.radians(-90.0), math.radians(0.0)
        angle = GeoCluster._greatcircle_angle(
            south_lat, south_lon, equator_lat, equator_lon
        )
        assert abs(angle - math.pi / 2) < 1e-10  # Should be 90°
