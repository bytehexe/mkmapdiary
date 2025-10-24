import numpy as np
from scipy.spatial import ConvexHull
import copy
from shapely.geometry import MultiPoint


class GeoCluster:
    def __init__(self, locations):
        # Interface expects locations as (lon, lat) tuples for consistency with GeoJSON
        self.__locations = locations

        self.__degrees, self.__distance, self.__midpoint = (
            self.__longest_greatcircle_separation()
        )

    EARTH_RADIUS_M = 6371008.8  # mean Earth radius in meters

    @property
    def locations(self):
        return copy.deepcopy(self.__locations)

    @property
    def separation_degrees(self):
        return self.__degrees

    @property
    def separation_meters(self):
        return self.__distance

    @property
    def midpoint(self):
        return copy.deepcopy(self.__midpoint)

    @property
    def shape(self):
        # MultiPoint expects (lon, lat) format which matches our interface
        return MultiPoint(self.__locations)

    @property
    def mass_point(self):
        if len(self.__locations) == 0:
            return (None, None)

        pts = np.array(self.__locations)
        # Convert from (lon, lat) interface to internal calculation format
        lon = np.radians(pts[:, 0])  # longitude from first column
        lat = np.radians(pts[:, 1])  # latitude from second column

        x = np.cos(lat) * np.cos(lon)
        y = np.cos(lat) * np.sin(lon)
        z = np.sin(lat)

        x_mean = np.mean(x)
        y_mean = np.mean(y)
        z_mean = np.mean(z)

        lon_mean = np.arctan2(y_mean, x_mean)
        hyp = np.sqrt(x_mean * x_mean + y_mean * y_mean)
        lat_mean = np.arctan2(z_mean, hyp)

        # Return as (lon, lat) to match interface format
        return (
            (np.degrees(lon_mean) + 540) % 360 - 180,  # normalize longitude [-180, 180]
            np.degrees(lat_mean),
        )

    @property
    def radius(self):
        return self.__distance / 2

    @property
    def zoom_level(self):
        if len(self.__locations) == 0:
            return 18  # max zoom

        if self.__degrees == 0:
            return 18  # max zoom

        # Level 0 is 360°, Level 1 is 180° and so on
        adjustment_factor = 2

        level = int(round(np.log2(360.0 / self.__degrees * adjustment_factor)))
        return max(min(level, 18), 3)

    @staticmethod
    def __greatcircle_angle(lat1, lon1, lat2, lon2):
        """Angular distance (radians) between two points on a sphere."""
        return np.arccos(
            np.clip(
                np.sin(lat1) * np.sin(lat2)
                + np.cos(lat1) * np.cos(lat2) * np.cos(lon1 - lon2),
                -1,
                1,
            )
        )

    @staticmethod
    def __greatcircle_midpoint(lat1, lon1, lat2, lon2):
        """Midpoint in radians between two points on a sphere. Returns (lat, lon) for internal calculations."""
        dlon = lon2 - lon1
        bx = np.cos(lat2) * np.cos(dlon)
        by = np.cos(lat2) * np.sin(dlon)
        lat3 = np.arctan2(
            np.sin(lat1) + np.sin(lat2), np.sqrt((np.cos(lat1) + bx) ** 2 + by**2)
        )
        lon3 = lon1 + np.arctan2(by, np.cos(lat1) + bx)
        return lat3, lon3

    def __longest_greatcircle_separation(self):
        """
        Returns:
        - separation_deg: angular separation in degrees
        - separation_m: great-circle distance in meters
        - midpoint: (lon, lat) in degrees to match interface format
        """
        pts = np.array(self.__locations)
        n = len(pts)

        if n < 2:
            return 0.0, 0.0, (None, None)

        # Handle 2-point case
        if n == 2:
            # Convert from (lon, lat) interface to internal calculation format
            lon1, lat1 = np.radians(pts[0])
            lon2, lat2 = np.radians(pts[1])
            ang = self.__greatcircle_angle(lat1, lon1, lat2, lon2)
            mid_lat, mid_lon = self.__greatcircle_midpoint(lat1, lon1, lat2, lon2)
            separation_m = ang * self.EARTH_RADIUS_M
            # Return midpoint as (lon, lat) to match interface format
            return (
                np.degrees(ang),
                separation_m,
                ((np.degrees(mid_lon) + 540) % 360 - 180, np.degrees(mid_lat)),
            )

        # Step 1: Convex hull to reduce comparisons
        hull = ConvexHull(pts)
        hull_pts = pts[hull.vertices]
        # Convert from (lon, lat) interface to internal calculation format
        lon = np.radians(hull_pts[:, 0])  # longitude from first column
        lat = np.radians(hull_pts[:, 1])  # latitude from second column

        # Step 2: Pairwise angular distances
        sin_lat = np.sin(lat)
        cos_lat = np.cos(lat)
        dlon = lon[:, None] - lon[None, :]
        central_angle = np.arccos(
            np.clip(
                sin_lat[:, None] * sin_lat[None, :]
                + cos_lat[:, None] * cos_lat[None, :] * np.cos(dlon),
                -1,
                1,
            )
        )

        # Step 3: Find maximum distance
        i, j = np.unravel_index(np.argmax(central_angle), central_angle.shape)
        ang = central_angle[i, j]
        separation_m = ang * self.EARTH_RADIUS_M

        # Step 4: Compute midpoint
        mid_lat, mid_lon = self.__greatcircle_midpoint(lat[i], lon[i], lat[j], lon[j])
        mid_lat_deg = np.degrees(mid_lat)
        mid_lon_deg = (np.degrees(mid_lon) + 540) % 360 - 180  # normalize [-180, 180]

        # Return midpoint as (lon, lat) to match interface format
        return np.degrees(ang), separation_m, (mid_lon_deg, mid_lat_deg)
