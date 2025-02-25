from contextlib import suppress
from datetime import datetime
from urllib.parse import urlparse, urlunsplit, urlsplit

import requests
from sq_browse.structs import BrowserResponse


class Browser(object):

    def __init__(self, **config):
        pass

    def browse(self, url) -> BrowserResponse:
        raise NotImplementedError

    def possible_urls(self, ambiguous_url) -> str:
        url_parts = list(urlsplit(ambiguous_url))

        # if only a domain was provided, it is detected as path and not as netloc
        if url_parts[2] and not all([*url_parts[:2], url_parts[3:]]):
            url_parts[2], url_parts[1] = url_parts[1], url_parts[2]

        if not url_parts[0]:
            yield urlunsplit(["https", *url_parts[1:]])
            yield urlunsplit(["http", *url_parts[1:]])
        else:
            yield urlunsplit(url_parts)


class RequestsBrowser(Browser):

    def browse(self, ambiguous_url: str) -> BrowserResponse:
        start = datetime.now()

        for url in self.possible_urls(ambiguous_url):
            with suppress(IOError):
                r = requests.get(url, timeout=2000)
                break
        else:
            raise IOError(f"No valid URL found for {ambiguous_url}")

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
