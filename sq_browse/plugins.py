from importlib.metadata import entry_points
from sq_browse import browser


def load_browser_plugins():
    discovered_plugins = entry_points(group='sq_browse.browser')

    for plugin in discovered_plugins:
        browser.registry.register(plugin.name, plugin.load(), {})
