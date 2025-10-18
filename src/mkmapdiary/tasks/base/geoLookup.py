from .httpRequest import HttpRequest
import threading
import time

lock = threading.Lock()


class GeoLookup(HttpRequest):

    def geoSearch(self, location):
        with lock:
            time.sleep(1)  # respect rate limit

            url = "https://nominatim.openstreetmap.org/search"
            headers = {"User-Agent": "mkmapdiary/0.1 travel-diary generator"}
            params = {"q": location, "format": "json", "limit": 1}
            return self.httpRequest(url, params, headers)

    def __decimals_for_zoom(self, zoom):
        if self.config["geo_lookup"]["high_precision"]:
            offset = 1
        else:
            offset = 0

        if zoom <= 4:
            return 0 + offset
        elif zoom <= 9:
            return 1 + offset
        else:
            return 2 + offset

    @staticmethod
    def __round_coord(coord, zoom):
        d = GeoLookup.__decimals_for_zoom(zoom)
        return round(coord, d)

    def geoReverse(self, lat, lon, zoom):
        zoom = max(1, min(zoom, 10))  # Clamp zoom

        with lock:
            time.sleep(1)  # respect rate limit

            url = "https://nominatim.openstreetmap.org/reverse"
            headers = {"User-Agent": "mkmapdiary/0.1 travel-diary generator"}
            params = {
                "lat": self.__round_coord(lat, zoom),
                "lon": self.__round_coord(lon, zoom),
                "format": "json",
                "zoom": zoom,
            }
            return self.httpRequest(url, params, headers)
