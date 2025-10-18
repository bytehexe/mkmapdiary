from .httpRequest import HttpRequest
import threading
import time

lock = threading.Lock()

class GeoLookup(HttpRequest):

    def geoSearch(self, location):
        with lock:
            time.sleep(1)  # respect rate limit

            url = "https://nominatim.openstreetmap.org/search"
            headers = {
                "User-Agent": "tdgen/0.1 travel-diary generator"
            }
            params = {
                "q": location,
                "format": "json",
                "limit": 1
            }
            return self.httpRequest(url, params, headers)

    @staticmethod
    def __decimals_for_zoom(zoom):
        return max(0, min(8, round(0.33 * zoom - 1.5)))

    @staticmethod
    def __round_coord(coord, zoom):
        d = GeoLookup.__decimals_for_zoom(zoom)
        return round(coord, d)

    def geoReverse(self, lat, lon, zoom):
        with lock:
            time.sleep(1)  # respect rate limit

            url = "https://nominatim.openstreetmap.org/reverse"
            headers = {
                "User-Agent": "tdgen/0.1 travel-diary generator"
            }
            params = {
                "lat": self.__round_coord(lat, zoom),
                "lon": self.__round_coord(lon, zoom),
                "format": "json",
                "zoom": zoom,
            }
            return self.httpRequest(url, params, headers)
