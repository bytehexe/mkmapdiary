from PIL import Image
from .base.baseTask import BaseTask
from .base.exifReader import ExifReader
import json, yaml
from jsonschema import validate
import pathlib
from lxml import etree
from itertools import zip_longest
from threading import Lock
import requests
import time

GPX_NS = "http://www.topografix.com/GPX/1/1"
NSMAP = {None: GPX_NS}

coder_lock = Lock()

class GeojsonTask(BaseTask, ExifReader):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_ext_geo_json(self, source):
        self.__sources.append(source)
        return []
    
    def handle_ext_geo_yaml(self, source):
        self.__sources.append(source)
        return []
    
    def __generate_destination_filename(self, source):
        filename = (self.assets_dir / source.stem).with_suffix(f"{source.suffix[0:2]}.gpx")
        return self.make_unique_filename(source, filename)

    @classmethod
    def __addPoint(cls, gpx, coordinates, properties, tag="wpt"):
        wpt = etree.SubElement(gpx, tag, lat=str(coordinates[1]), lon=str(coordinates[0]))
        if len(coordinates) > 2 and coordinates[2] is not None:
            etree.SubElement(wpt, "ele").text = str(coordinates[2])
        if properties.get("time") is not None:
            etree.SubElement(wpt, "time").text = str(properties["time"])
        if properties.get("name") is not None:
            etree.SubElement(wpt, "name").text = str(properties["name"])
        if properties.get("type") is not None:
            etree.SubElement(wpt, "type").text = str(properties["type"])
        if properties.get("symbol") is not None:
            etree.SubElement(wpt, "sym").text = str(properties["symbol"])
        return wpt

    @classmethod
    def __addLineString(cls, gpx, coordinates, properties):
        trk = etree.SubElement(gpx, "trk")
        if "name" in properties:
            etree.SubElement(trk, "name").text = str(properties["name"])
        trkseg = etree.SubElement(trk, "trkseg")

        items = list(zip_longest(
            coordinates,
            properties.get("names", []),
            properties.get("timestamps", []),
            properties.get("types", []),
            properties.get("symbols", []),
            fillvalue=None))

        for coord, name, ts, ty, sym in items:
            cls.__addPoint(trkseg, coord, {
                "name": name,
                "time": ts,
                "type": ty,
                "symbol": sym
            }, tag="trkpt")
        return trkseg
    
    def __nominatim_query(self, location):
        # get geocoder lock
        with coder_lock:
            print(f"Looking up location: {location}")
            time.sleep(1)  # respect rate limit

            print("Querying Nominatim...")
            r = requests.get("https://nominatim.openstreetmap.org/", params={
                "q": location,
                "format": "json",
                "limit": 1
            }, headers={
                "User-Agent": "tdgen travel-diary generator"
            }, timeout=4)
            r.raise_for_status()
            results = r.json()
            return results


    def __lookup(self, lookup):
        # lookup can be coordinates
        if isinstance(lookup, list) and len(lookup) in (2, 3):
            return lookup
        

        data = self.__nominatim_query(lookup)

        location = data[0] if data else None

        if location is None:
            raise ValueError(f"Could not lookup location: {lookup}")
        
        return [location["lat"], location["lon"]]

    def task_geo2gpx(self):
        """Convert a geojson or geoyaml file to gpx."""
        
        def _convert(src, dst):
            ext = src.suffix
            if ext == ".yaml":
                loader = yaml.safe_load
            elif ext == ".json":
                loader = json.load
            else:
                raise ValueError(f"Invalid extension: {ext}")
            
            script_dir = pathlib.Path(__file__).parent
            with open(script_dir.parent / "extras" / "geo.schema.yaml") as f:
                schema = yaml.safe_load(f)

            with open(src) as f:
                data = loader(f)

            validate(instance=data, schema=schema)

            gpx = etree.Element(
                "gpx",
                nsmap=NSMAP,
                version="1.1",
                creator="tdgen"
            )

            for feature in data["features"]:
                if feature["geometry"] is None:
                    # lookup type - check if Point or LineString
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

            # write gpx to file
            tree = etree.ElementTree(gpx)
            tree.write(dst, xml_declaration=True, encoding="utf-8", pretty_print=True)

        for src in self.__sources:
            dst = self.__generate_destination_filename(src)
            yield dict(
                    name=dst,
                    actions=[(_convert, (src, dst))],
                    file_dep=[src],
                    task_dep=[f"create_directory:{dst.parent}"],
                    targets=[dst],
                )