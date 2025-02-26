import signal
from contextlib import suppress
from datetime import datetime
from urllib.parse import urlparse, urlunsplit, urlsplit

import requests
from sq_browse.structs import BrowserResponse


class ForcedTimeout(object):

    def __init__(self, timeout):
        self.timeout = timeout

    @staticmethod
    def raise_timeout(signum, stack):
        raise TimeoutError("Forced timeout")

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)


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
    HEADERS = {
        "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/132.0.0.0 Safari/537.36")
    }

    def __init__(self, **config):
        super().__init__(**config)
        self.timeout = 3

    def browse(self, ambiguous_url: str) -> BrowserResponse:
        start = datetime.now()

        for url in self.possible_urls(ambiguous_url):
            with suppress(IOError, TimeoutError), ForcedTimeout(self.timeout):
                r = requests.get(url, timeout=self.timeout+0.001, headers=self.HEADERS)
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
registry.register("requests", RequestsBrowser, {})
