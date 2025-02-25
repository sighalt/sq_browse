from importlib.metadata import entry_points
from sq_browse import browser, postprocessing


def load_browser_plugins():
    discovered_plugins = entry_points(group='sq_browse.browser')

    for plugin in discovered_plugins:
        browser.registry.register(plugin.name, plugin.load(), {})


def load_processor_plugins():
    discovered_plugins = entry_points(group='sq_browse.processor')

    for plugin in discovered_plugins:
        processor_cls = plugin.load()
        postprocessing.pipeline.add_component(plugin.name, processor_cls())


def load_all_plugins():
    load_browser_plugins()
    load_processor_plugins()
