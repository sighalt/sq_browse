import os
import sys
import json
import argparse
import dataclasses
from datetime import datetime
from json import JSONDecodeError

from sq_browse.browser import registry
from sq_browse.postprocessing import pipeline


def json_decode_fallback(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise JSONDecodeError


def main(*argv):
    """Commandline entry point for sq_browse."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("url")
    arg_parser.add_argument("--browser", "-b", default="requests")

    args = arg_parser.parse_args(argv or sys.argv[1:])
    browser = registry.get_browser(args.browser)

    response = browser.browse(ambiguous_url=args.url)
    data = pipeline.run(response)

    # del data["raw"]["content"]
    try:
        json.dump(data, sys.stdout, default=json_decode_fallback)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


if __name__ == '__main__':
    main()
