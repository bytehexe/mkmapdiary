from .baseTask import BaseTask
import requests


class HttpRequest(BaseTask):
    def __init__(self):
        super().__init__()

    def httpRequest(self, url, data, headers, json=True):

        req = requests.Request("GET", url, params=data, headers=headers)
        prepared = req.prepare()

        assert "?" in prepared.url or not data

        return self.with_cache(
            "http-request",
            self.__send_request,
            prepared,
            json,
            cache_args=(prepared.url, json),
        )

    def __send_request(self, prepared, json):

        with requests.Session() as session:
            response = session.send(prepared, timeout=5)
            response.raise_for_status()

            if json:
                return response.json()
            else:
                return response.text
