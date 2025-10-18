from PIL import Image
from .base.baseTask import BaseTask
from .base.geoLookup import GeoLookup
import json, yaml
from jsonschema import validate
import pathlib
import gpxpy
import gpxpy.gpx
import dateutil
from itertools import zip_longest
from threading import Lock
import requests
import time

coder_lock = Lock()

class GeojsonTask(GeoLookup):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_ext_geo_json(self, source):
        return self.__handle(source)
    
    def handle_ext_geo_yaml(self, source):
        return self.__handle(source)
    
    def __handle(self, source):
        self.__sources.append(source)
        intermediate_file = self.__generate_destination_filename(source)

        # Load and validate file
        data = self.__load_file(source)
        script_dir = pathlib.Path(__file__).parent
        with open(script_dir.parent / "extras" / "geo.schema.yaml") as f:
            schema = yaml.safe_load(f)
        validate(instance=data, schema=schema)

        # Extract dates
        dates = self.__extract_dates(data)

        assets = list(self.handle_gpx(intermediate_file))
        return assets

    def __extract_dates(self, data):
        dates = set()
        for feature in data["features"]:
            props = feature.get("properties", {})
            if "timestamp" in props:
                dates.add(dateutil.parser.isoparse(props["timestamp"]).date())
            if "timestamps" in props:
                for ts in props["timestamps"]:
                    dates.add(dateutil.parser.isoparse(ts).date())
        return dates

    def __generate_destination_filename(self, source):
        filename = (self.files_dir / source.stem).with_suffix(f"{source.suffix[0:2]}.gpx")
        return self.make_unique_filename(source, filename)

    @classmethod
    def __parseDate(cls, dt):
        if dt is None:
            return None
        else:
            return dateutil.parser.isoparse(dt)

    @classmethod
    def __addPoint(cls, gpx, coordinates, properties, tag="wpt"):
        if tag == "wpt":
            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=coordinates[1], longitude=coordinates[0],
                elevation=coordinates[2] if len(coordinates) > 2 and coordinates[2] is not None else None,
                time=cls.__parseDate(properties.get("timestamp")),
                name=properties.get("name"),
                type=properties.get("type"),
                symbol=properties.get("symbol"),
                position_dilution=properties.get("pdop"),
            )
            gpx.waypoints.append(wpt)
            return wpt
        elif tag == "trkpt":
            assert properties.get("type") == None
            pt = gpxpy.gpx.GPXTrackPoint(
                latitude=coordinates[1], longitude=coordinates[0],
                elevation=coordinates[2] if len(coordinates) > 2 and coordinates[2] is not None else None,
                time=cls.__parseDate(properties.get("timestamp")),
                name=properties.get("name"),
                symbol=properties.get("symbol"),
                position_dilution=properties.get("pdop"),
                
            )
            return pt

    @classmethod
    def __addLineString(cls, gpx, coordinates, properties):
        trk = gpxpy.gpx.GPXTrack(name=properties.get("name"))
        trkseg = gpxpy.gpx.GPXTrackSegment()
        items = list(zip_longest(
            coordinates,
            properties.get("names", []),
            properties.get("timestamps", []),
            properties.get("types", []),
            properties.get("symbols", []),
            fillvalue=None))
        for coord, name, ts, ty, sym in items:
            pt = cls.__addPoint(None, coord, {
                "name": name,
                "timestamp": ts,
                "type": ty,
                "symbol": sym
            }, tag="trkpt")
            trkseg.points.append(pt)
        trk.segments.append(trkseg)
        gpx.tracks.append(trk)
        return trkseg
    

    def __lookup(self, lookup):
        # lookup can be coordinates
        if isinstance(lookup, list) and len(lookup) in (2, 3):
            return lookup
        
        data = self.geoSearch(lookup)

        location = data[0] if data else None

        if location is None:
            raise ValueError(f"Could not lookup location: {lookup}")
        
        return [location["lat"], location["lon"]]

    def __load_file(self, source):
        ext = source.suffix
        if ext == ".yaml":
            loader = yaml.safe_load
        elif ext == ".json":
            loader = json.load
        else:
            raise ValueError(f"Invalid extension: {ext}")
        with open(source) as f:
            data = loader(f)
        return data

    def task_geo2gpx(self):
        """Convert a geojson or geoyaml file to gpx using gpxpy."""
        def _convert(src, dst):
            data = self.__load_file(src)

            gpx = gpxpy.gpx.GPX()
            gpx.creator = "tdgen"
            for feature in data["features"]:
                if feature["geometry"] is None:
                    lookup_type = type(feature["properties"]["lookup"])
                    if lookup_type is list:
                        feature["geometry"] = {
                            "type": "LineString",
                            "coordinates": [self.__lookup(x) for x in feature["properties"]["lookup"]]
                        }
                    else:
                        feature["geometry"] = {
                            "type": "Point",
                            "coordinates": self.__lookup(feature["properties"]["lookup"])
                        }
                if feature["geometry"]["type"] == "Point":
                    self.__addPoint(gpx, feature["geometry"]["coordinates"], feature.get("properties", {}))
                elif feature["geometry"]["type"] == "LineString":
                    self.__addLineString(gpx, feature["geometry"]["coordinates"], feature.get("properties", {}))
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