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
    
    def geoReverse(self, lat, lon):
        with lock:
            time.sleep(1)  # respect rate limit

            url = "https://nominatim.openstreetmap.org/reverse"
            headers = {
                "User-Agent": "tdgen/0.1 travel-diary generator"
            }
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json"
            }
            return self.httpRequest(url, params, headers)
