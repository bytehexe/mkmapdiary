import numpy as np
from scipy.spatial import ConvexHull
import math


def object_level(points):
    """
    Returns OSM tile level for the cluster with the given points.
    """
    pts = np.array(points)
    if len(pts) < 2:
        return 18

    if len(pts) == 2:
        # Direct great-circle angle for two points
        lat1, lon1 = np.radians(pts[0])
        lat2, lon2 = np.radians(pts[1])
        degrees = np.degrees(
            np.arccos(
                np.clip(
                    np.sin(lat1) * np.sin(lat2)
                    + np.cos(lat1) * np.cos(lat2) * np.cos(lon1 - lon2),
                    -1,
                    1,
                )
            )
        )

    else:
        # Step 1: approximate convex hull on lat/lon plane
        # (works well unless all points are nearly on a line)
        hull = ConvexHull(pts)
        hull_pts = pts[hull.vertices]

        # Step 2: compute all pairwise haversine distances on hull vertices
        lat = np.radians(hull_pts[:, 0])
        lon = np.radians(hull_pts[:, 1])

        # Vectorized computation
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

        degrees = np.degrees(np.max(central_angle))

    # Level 0 is 360°, Level 1 is 180° and so on

    adjustment_factor = 2

    level = int(round(math.log(360.0 / degrees * adjustment_factor)))
    return max(min(level, 18), 3)


if __name__ == "__main__":
    points = [
        # (48.8566, 2.3522),    # Paris
        # (47.6559, -2.7603),   # Vannes
        # (40.7128, -74.0060),  # New York
        # (35.6895, 139.6917),  # Tokyo
        # (-33.8688, 151.2093)  # Sydney
        (48.881111, 2.355278),  # Gare du nord
        (48.84, 2.318611),  # Gare Montparnasse
        (43.7045, 7.262),  # Nice
    ]

    print(object_level(points))
