from typing import Any

import requests

from .baseTask import BaseTask


class HttpRequest(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    def httpRequest(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: bool = True,
    ) -> dict[str, Any] | str:
        req = requests.Request("GET", url, params=data, headers=headers)
        prepared = req.prepare()

        assert prepared.url is not None, "Prepared URL should not be None"
        assert "?" in prepared.url or not data

        return self.with_cache(
            "http-request",
            self.__send_request,
            prepared,
            json,
            cache_args=(prepared.url, json),
        )

    def __send_request(
        self, prepared: requests.PreparedRequest, json: bool
    ) -> dict[str, Any] | str:
        with requests.Session() as session:
            response = session.send(prepared, timeout=5)
            response.raise_for_status()

            if json:
                return response.json()
            else:
                return response.text
