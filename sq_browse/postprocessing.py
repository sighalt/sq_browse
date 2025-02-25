import abc
from collections import deque
from logging import warning
from urllib.parse import urljoin
from xml.etree.ElementTree import Element

from lxml import html
from typing import Dict, List, Type

from sq_browse import html_utils
from sq_browse.errors import UnprocessableError
from sq_browse.html_utils import get_text
from sq_browse.structs import BrowserResponse


def first_or_none(elems):
    return elems[0] if elems else None


def xpath_extract(elem, path, clean=True):
    result = first_or_none(elem.xpath(path))

    if result and clean:
        return result.strip()

    return result


class BaseProcessor(abc.ABC):
    dependencies = []

    def __init__(self, **kwargs):
        pass

    def process(self, data: Dict) -> Dict:
        return data


class LxmlProcessor(BaseProcessor):

    def process(self, data: Dict) -> Dict:
        data = super().process(data)
        try:
            data["_tree"] = html.fromstring(data["raw"]["content"], base_url=data["meta"]["url"])
        except ValueError:
            data["_tree"] = html.fromstring(data["raw"]["content"].encode("utf-8"), base_url=data["meta"]["url"])

        return data


class TextProcessor(BaseProcessor):
    dependencies = ["lxml"]

    def process(self, data: Dict) -> Dict:
        data = super().process(data)
        tree: html.HtmlElement = data["_tree"]
        body = tree.find("body")

        main = body.find("main")

        main_text = html_utils.get_text(main if main is not None else body)
        main_text = "\n".join([line.strip() for line in main_text.splitlines()])
        data["content"]["text"] = main_text

        return data


class MetadataProcessor(BaseProcessor):
    dependencies = ["lxml"]

    def process(self, data: Dict) -> Dict:
        tree = data["_tree"]
        custom_metadata = {}
        metadata = {
            "title": xpath_extract(tree, "//title/text()"),
            "heading": get_text(tree.xpath("//h1")[0]) if len(tree.xpath("//h1")) else None,
            "description": xpath_extract(tree, "//meta[@name='description']/@content"),
            "keywords": xpath_extract(tree, "//meta[@name='keywords']/@content"),
            "author": xpath_extract(tree, "//meta[@name='author']/@content"),
            "custom": custom_metadata,
        }

        for meta_elem in tree.xpath("//head//meta"):
            name = xpath_extract(meta_elem, "./@name", clean=False)
            value = xpath_extract(meta_elem, "./@content", clean=False)

            if name and name not in ["description", "keywords", "author"]:
                custom_metadata[name] = value

        data["content"]["metadata"] = metadata

        return data


class LinkProcessor(BaseProcessor):
    dependencies = ["lxml"]

    def process(self, data: Dict) -> Dict:
        links = data["_tree"].xpath("//a")
        link_list = [
            {
                "title": "".join(link.xpath(".//text()")).strip(),
                "href": urljoin(data["meta"]["url"], link.attrib["href"]),
            }
            for link
            in links
            if "href" in link.attrib and not link.attrib["href"].startswith("#")
        ]
        data["_links"] = list(filter(lambda x: len(x["title"]), link_list))

        return data


class TableProcessor(BaseProcessor):
    dependencies = ["lxml"]

    def process(self, data: Dict) -> Dict:
        result_data = []
        tables = data["_tree"].xpath("//table")

        for table in tables:
            table_data = self.process_table_plain(table)
            result_data.append(table_data)

        data["content"]["tables"] = result_data

        return data

    def process_table_plain(self, table: Element) -> Dict:
        table_data = {
            "rows": []
        }
        columns = self.column_names(table)

        if head_data := self.parse_table_head(table):
            table_data["head"] = head_data

        for row in table.xpath(".//tr[not(ancestor::*[local-name()='tfoot' or local-name()='thead'])]"):
            row_data = self.parse_row(row, columns=columns)

            # ignore if this is the semantic header row
            if columns and (isinstance(row_data, dict) and tuple(row_data.values()) == columns) or row_data == columns:
                continue

            table_data["rows"].append(row_data)

        if foot_data := self.parse_table_foot(table):
            table_data["foot"] = foot_data

        return table_data

    def column_names(self, table: Element) -> tuple | None:
        # rows which have only th members (everything other than th/td is ignored though)
        candidates = table.xpath(".//tr[not(descendant::*[local-name()='td' or local-name()='th']"
                                 "[not(local-name()='th')])]")

        if len(candidates) == 1:
            column_names = self.parse_row(candidates[0])

            # make sure there are no duplicates
            if len(column_names) == len(set(column_names)):
                return column_names

    def parse_table_foot(self, table: Element) -> List[tuple] | None:
        tfoot = table.find(".//tfoot")
        row_data = []

        if tfoot is not None:
            for row in tfoot.xpath(".//tr"):
                row_data.append(self.parse_row(row))

            return row_data

    def parse_table_head(self, table: Element) -> List[tuple] | None:
        tfoot = table.find(".//thead")
        row_data = []

        if tfoot is not None:
            for row in tfoot.xpath(".//tr"):
                row_data.append(self.parse_row(row))

            return row_data

            return row_data

    def parse_row(self, row: Element, columns: tuple = None) -> tuple|dict:
        cells = row.xpath(".//*[local-name() = 'td' or local-name() = 'th']")

        if columns and len(cells) == len(columns):
            return {
                column: get_text(cell)
                for column, cell
                in zip(columns, cells)
            }

        return tuple([get_text(cell) for cell in cells])


class Pipeline(object):

    def __init__(self):
        self.components: Dict[str, BaseProcessor] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def add_component(self, name: str, component: BaseProcessor):
        self.components[name] = component
        self.dependencies[name] = component.dependencies

    def run(self, response: BrowserResponse, fail_save=True) -> Dict:
        data = {
            "meta": {
                "elapsed": response.elapsed.total_seconds(),
                "timestamp": response.timestamp_start,
                "url": response.url,
                "requested_url": response.requested_url,
            },
            "raw": {
                "headers": response.response_headers,
                "content": response.content,
                "status_code": response.status_code,
                "reason": response.reason,
            },
            "content": {},
        }

        for component in self.iter_components():
            try:
                data = component.process(data)
            except Exception as e:
                if fail_save:
                    warning(f"Could not process data with {component.__class__.__name__}: {e!r}")
                else:
                    raise UnprocessableError(str(e))

        self._clean_data(data)

        return data

    @staticmethod
    def _clean_data(data: Dict):
        """Remove all keys starting with _"""
        for key in list(data.keys()):
            if key.startswith("_"):
                del data[key]

        del data["raw"]["content"]

    def iter_components(self):
        """Iterate over all components in the correct order, such that all dependencies are met."""
        for component_name in self.sorted_components():
            yield self.components[component_name]

    def sorted_components(self) -> List[str]:
        """Sort components such that every component occurs after its dependencies.

        Uses an implementation of Kahn's algorithm.
        :return:
        """
        result = []
        deps = {
            k: set(v)
            for k, v
            in self.dependencies.items()
        }
        without_edges = {
            component
            for component
            in self.components.keys()
            if len(deps[component]) == 0
        }

        while len(without_edges) > 0:
            node = without_edges.pop()
            result.append(node)

            for other_node, other_dep in deps.items():
                try:
                    other_dep.remove(node)
                except KeyError:
                    continue

                if len(other_dep) == 0:
                    without_edges.add(other_node)

        return result


class SemanticLinkProcessor(BaseProcessor):
    dependencies = ["links"]

    def process(self, data: Dict) -> Dict:
        links = {}
        seen = set()

        for link_data in data["_links"]:
            link_class = self.classify_link_title(link_data["title"])

            if link_class and link_class not in seen:
                links[link_class] = link_data["href"]
                seen.add(link_class)

        data["content"]["links"] = links

        return data

    def classify_link_title(self, link_title: str) -> str|None:
        link_title = link_title.lower().strip()

        if link_title in ("impressum", "imprint", "legal notice"):
            return "Imprint"

        elif link_title in ("kontakt", "contact", "contact us"):
            return "Contact"


pipeline = Pipeline()
pipeline.add_component("lxml", LxmlProcessor())
pipeline.add_component("text", TextProcessor())
pipeline.add_component("metadata", MetadataProcessor())
pipeline.add_component("links", LinkProcessor())
pipeline.add_component("table", TableProcessor())
pipeline.add_component("semantic_links", SemanticLinkProcessor())
