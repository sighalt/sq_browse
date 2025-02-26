import os
import sys
import json
import argparse
from datetime import datetime
from json import JSONDecodeError

from sq_browse.browser import registry
from sq_browse.plugins import load_all_plugins
from sq_browse.postprocessing import pipeline


def json_decode_fallback(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise JSONDecodeError


def cmd_run(args):
    browser = registry.get_browser(args.browser)

    response = browser.browse(ambiguous_url=args.url)
    data = pipeline.run(response)

    try:
        json.dump(data, sys.stdout, default=json_decode_fallback)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


def cmd_run_subprocess(args):
    browser = registry.get_browser(args.browser)

    while True:
        try:
            url = sys.stdin.readline().strip()
            response = browser.browse(ambiguous_url=url)
            data = pipeline.run(response, fail_save=False)
            json.dump(data, sys.stdout, default=json_decode_fallback)
            sys.stdout.write("\n")
            sys.stdout.flush()
        except KeyboardInterrupt:
            return
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"{e.__class__.__name__}: {str(e).strip()}\n")
            sys.stderr.flush()
            continue


def cmd_config(args):
    print("Browsers:")
    for name, browser_cls in registry.browsers.items():
        print(f"- {name:15s}\t{browser_cls.__module__}.{browser_cls.__name__}")

    print("")

    print("Processors:")
    for processor_name in pipeline.sorted_components():
        processor = pipeline.components[processor_name]
        print(f"- {processor_name:15s}\t{processor.__module__}.{processor.__class__.__name__}")


def main(*argv):
    """Commandline entry point for sq_browse."""
    arg_parser = argparse.ArgumentParser()
    sub_parsers = arg_parser.add_subparsers(title="command", required=True)

    run_parser = sub_parsers.add_parser("run")
    run_parser.set_defaults(func=cmd_run)
    run_parser.add_argument("url")
    run_parser.add_argument("--browser", "-b", default="requests")

    run_subproc_parser = sub_parsers.add_parser("run-subprocess")
    run_subproc_parser.set_defaults(func=cmd_run_subprocess)
    run_subproc_parser.add_argument("--browser", "-b", default="requests")

    config_parser = sub_parsers.add_parser("config")
    config_parser.set_defaults(func=cmd_config)

    args = arg_parser.parse_args(argv or sys.argv[1:])
    load_all_plugins()

    args.func(args)


if __name__ == '__main__':
    main()
