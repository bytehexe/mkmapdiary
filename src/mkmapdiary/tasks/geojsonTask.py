import json
import pathlib
from datetime import datetime
from itertools import zip_longest
from pathlib import PosixPath
from threading import Lock
from typing import Any, Dict, Iterator, List, Optional, Union

import dateutil
import gpxpy
import gpxpy.gpx
import yaml
from jsonschema import validate

from .base.geoLookup import GeoLookup
from .gpxTask import GPXTask

coder_lock = Lock()


class GeojsonTask(GeoLookup, GPXTask):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def handle_ext_geo_json(self, source: PosixPath) -> List[Any]:
        return self.__handle(source)

    def handle_ext_geo_yaml(self, source: pathlib.PosixPath) -> List[Any]:
        return self.__handle(source)

    def __handle(self, source: PosixPath) -> List[Any]:
        self.__sources.append(source)
        intermediate_file = self.__generate_destination_filename(source)

        assets = list(self.handle_gpx(intermediate_file))
        return assets

    def __generate_destination_filename(self, source: PosixPath) -> PosixPath:
        filename = PosixPath(self.dirs.files_dir / source.stem).with_suffix(
            f"{source.suffix[0:2]}.gpx",
        )
        return self.make_unique_filename(source, filename)

    @classmethod
    def _parseDate(cls, dt: Optional[str]) -> Optional[datetime]:
        if dt is None:
            return None
        else:
            return dateutil.parser.isoparse(dt)

    @classmethod
    def __addPoint(
        cls,
        gpx: Optional[gpxpy.gpx.GPX],
        coordinates: Any,
        properties: Dict[str, Any],
        tag: str = "wpt",
    ) -> Optional[Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXTrackPoint]]:
        if tag == "wpt":
            # Convert from GeoJSON coordinates [lon, lat] to GPX format (lat, lon)
            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=coordinates[1],  # lat from second element
                longitude=coordinates[0],  # lon from first element
                elevation=(
                    coordinates[2]
                    if len(coordinates) > 2 and coordinates[2] is not None
                    else None
                ),
                time=cls._parseDate(properties.get("timestamp")),
                name=properties.get("name"),
                type=properties.get("type"),
                symbol=properties.get("symbol"),
                position_dilution=properties.get("pdop"),
            )
            if gpx is not None:
                gpx.waypoints.append(wpt)
            return wpt
        elif tag == "trkpt":
            assert properties.get("type") is None
            # Convert from GeoJSON coordinates [lon, lat] to GPX format (lat, lon)
            pt = gpxpy.gpx.GPXTrackPoint(
                latitude=coordinates[1],  # lat from second element
                longitude=coordinates[0],  # lon from first element
                elevation=(
                    coordinates[2]
                    if len(coordinates) > 2 and coordinates[2] is not None
                    else None
                ),
                time=cls._parseDate(properties.get("timestamp")),
                name=properties.get("name"),
                symbol=properties.get("symbol"),
                position_dilution=properties.get("pdop"),
            )
            return pt
        return None

    @classmethod
    def __addLineString(
        cls, gpx: gpxpy.gpx.GPX, coordinates: List[Any], properties: Dict[str, Any]
    ) -> gpxpy.gpx.GPXTrackSegment:
        trk = gpxpy.gpx.GPXTrack(name=properties.get("name"))
        trkseg = gpxpy.gpx.GPXTrackSegment()
        items = list(
            zip_longest(
                coordinates,
                properties.get("names", []),
                properties.get("timestamps", []),
                properties.get("types", []),
                properties.get("symbols", []),
                fillvalue=None,
            ),
        )
        for coord, name, ts, ty, sym in items:
            pt = cls.__addPoint(
                None,
                coord,
                {"name": name, "timestamp": ts, "type": ty, "symbol": sym},
                tag="trkpt",
            )
            if pt is not None:
                trkseg.points.append(pt)  # type: ignore
        trk.segments.append(trkseg)
        gpx.tracks.append(trk)
        return trkseg

    def __lookup(self, lookup: Union[str, List[float]]) -> List[float]:
        # lookup can be coordinates - expects/returns (lon, lat) format for GeoJSON compatibility
        if isinstance(lookup, list) and len(lookup) in (2, 3):
            return lookup

        if isinstance(lookup, str):
            data = self.geoSearch(lookup)
        else:
            raise ValueError(f"Invalid lookup type: {type(lookup)}")

        location = data[0] if data else None

        if location is None:
            raise ValueError(f"Could not lookup location: {lookup}")

        # Convert from Nominatim response (lat, lon) to GeoJSON format (lon, lat)
        return [location["lon"], location["lat"]]

    def __load_file(self, source: PosixPath) -> Dict[str, Any]:
        ext = source.suffix
        with open(source) as f:
            if ext == ".yaml":
                data = yaml.safe_load(f)
            elif ext == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Invalid extension: {ext}")
        return data

    def task_geo2gpx(self) -> Iterator[Dict[str, Any]]:
        """Convert a geojson or geoyaml file to gpx using gpxpy."""

        def _convert(src: PosixPath, dst: PosixPath) -> None:
            data = self.__load_file(src)

            # Validate file
            with open(self.dirs.resources_dir / "geo.schema.yaml") as f:
                schema = yaml.safe_load(f)
            validate(instance=data, schema=schema)

            gpx = gpxpy.gpx.GPX()
            gpx.creator = "mkmapdiary"
            for feature in data["features"]:
                if feature["geometry"] is None:
                    lookup_type = type(feature["properties"]["lookup"])
                    if lookup_type is list:
                        feature["geometry"] = {
                            "type": "LineString",
                            "coordinates": [
                                self.__lookup(x)
                                for x in feature["properties"]["lookup"]
                            ],
                        }
                    else:
                        feature["geometry"] = {
                            "type": "Point",
                            "coordinates": self.__lookup(
                                feature["properties"]["lookup"],
                            ),
                        }
                if feature["geometry"]["type"] == "Point":
                    self.__addPoint(
                        gpx,
                        feature["geometry"]["coordinates"],
                        feature.get("properties", {}),
                    )
                elif feature["geometry"]["type"] == "LineString":
                    self.__addLineString(
                        gpx,
                        feature["geometry"]["coordinates"],
                        feature.get("properties", {}),
                    )
            with open(dst, "w", encoding="utf-8") as f:
                f.write(gpx.to_xml())

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                name=dst,
                actions=[(_convert, (src, dst))],
                file_dep=[src],
                task_dep=[f"create_directory:{dst.parent}"],
                targets=[dst],
            )
