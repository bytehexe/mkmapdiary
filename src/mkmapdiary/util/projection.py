import math

from pyproj import CRS, Transformer
from shapely.ops import transform


class LocalProjection:
    @staticmethod
    def __get_local_projection(lon, lat):
        # Interface uses (lon, lat) format for consistency with GeoJSON and web standards
        # UPS zones
        if lat >= 84:
            return CRS.from_epsg(32661)  # UPS North
        elif lat <= -80:
            return CRS.from_epsg(32761)  # UPS South

        # UTM zones
        zone = int(math.floor((lon + 180) / 6) + 1)
        hemisphere = "north" if lat >= 0 else "south"
        epsg_code = 32600 + zone if hemisphere == "north" else 32700 + zone
        return CRS.from_epsg(epsg_code)

    def __init__(self, shape):
        centroid = shape.centroid

        # pick CRS dynamically - centroid.x is longitude, centroid.y is latitude (Shapely uses (x=lon, y=lat))
        self.__crs_proj = self.__get_local_projection(centroid.x, centroid.y)
        self.__crs_wgs = "EPSG:4326"

        self.__transformer_to_proj = Transformer.from_crs(
            self.__crs_wgs, self.__crs_proj, always_xy=True
        )
        self.__transformer_to_wgs = Transformer.from_crs(
            self.__crs_proj, self.__crs_wgs, always_xy=True
        )

    def to_local(self, shape):
        return transform(self.__transformer_to_proj.transform, shape)

    def to_wgs(self, shape):
        return transform(self.__transformer_to_wgs.transform, shape)
