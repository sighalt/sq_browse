from datetime import datetime

import requests
from sq_browse.structs import BrowserResponse


class Browser(object):

    def __init__(self, **config):
        pass

    def browse(self, url) -> BrowserResponse:
        raise NotImplementedError


class RequestsBrowser(Browser):

    def browse(self, url: str) -> BrowserResponse:
        start = datetime.now()
        r = requests.get(url)

        return BrowserResponse(
            url=r.url,
            requested_url=url,
            status_code=r.status_code,
            reason=r.reason,
            response_headers={
                k.lower(): v
                for k, v
                in r.headers.items()
            },
            content=r.content.decode(r.apparent_encoding),
            timestamp_start=start,
            elapsed=r.elapsed,
        )


class BrowserRegistry(object):

    def __init__(self):
        self.browsers = {}
        self.browser_configs = {}

    def register(self, name: str, browser_cls, config: dict):
        self.browsers[name] = browser_cls
        self.browser_configs[name] = config

    def get_browser(self, name: str):
        browser_cls = self.browsers.get(name)
        config = self.browser_configs.get(name, {})

        return browser_cls(**config)


registry = BrowserRegistry()
registry.register('requests', RequestsBrowser, {})
