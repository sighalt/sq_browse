from datetime import timedelta, datetime
from unittest import TestCase

from sq_browse.postprocessing import Pipeline, TableProcessor, LxmlProcessor
from sq_browse.structs import BrowserResponse


class TestTableProcessor(TestCase):
    EXAMPLES = [
        (
            "simple_table_no_heading",
            """<table><tr><td>Anton</td><td>1</td></tr><tr><td>Berta</td><td>2</td></tr></table>""",
            {"rows": [("Anton", "1"), ("Berta", "2"),]},
        ),
        (
            "simple_table_no_semantic_th",
            """<table><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr></table>""",
            {"rows": [("Anton", "1"), ("Berta", "2"),]},
        ),
        (
            "simple_table_with_foot",
            """<table><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr><tfoot><tr><td colspan=2></td></tr></tdfoot></table>""",
            {"rows": [("Anton", "1"), ("Berta", "2"),], "foot": [("",)]},
        ),
        (
            "simple_table_with_head_and_foot",
            """<table><thead><tr><th>Name</th><th>Number</th></tr></thead><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr><tfoot><tr><td colspan=2></td></tr></tdfoot></table>""",
            {"head": [("Name", "Number")], "rows": [{"Name": "Anton", "Number": "1"}, {"Name": "Berta", "Number": "2"},], "foot": [("",)]},
        ),
        (
            "table_with_semantic_columns_in_thead",
            """<table><thead><tr><th>Name</th><th>Number</th></tr><tr><th>Anton</th><td>1</td></tr></thead><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr><tfoot><tr><td colspan=2></td></tr></tdfoot></table>""",
            {"head": [("Name", "Number"), ("Anton", "1")], "rows": [{"Name": "Anton", "Number": "1"}, {"Name": "Berta", "Number": "2"},], "foot": [("",)]},
        ),
        (
            "table_with_semantic_columns",
            """<table><tr><th>Name</th><th>Number</th></tr><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr></table>""",
            {"rows": [{"Name": "Anton", "Number": "1"}, {"Name": "Berta", "Number": "2"},]},
        ),
        (
            "table_with_semantic_columns_with_some_elements",
            """<table><tr><th>Name</th><th><span>Number</span></th></tr><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr></table>""",
            {"rows": [{"Name": "Anton", "Number": "1"}, {"Name": "Berta", "Number": "2"},]},
        ),
        (
            "table_with_semantic_columns_but_duplicate_column_names",
            """<table><tr><th>Name</th><th>Name</th></tr><tr><th>Anton</th><td>1</td></tr><tr><th>Berta</th><td>2</td></tr></table>""",
            {"rows": [("Name", "Name"), ("Anton", "1"), ("Berta", "2"),]},
        ),
    ]

    def setUp(self):
        self.pipeline = Pipeline()
        self.pipeline.add_component("lxml", LxmlProcessor())
        self.pipeline.add_component("table", TableProcessor())

    def test_examples(self):
        for name, example, true_value in self.EXAMPLES:
            with self.subTest(name=name):
                response = self.build_mock_response(example)
                pipeline_result = self.pipeline.run(response)

                self.assertEqual(1, len(pipeline_result["content"]["tables"]))
                self.assertEqual(true_value, pipeline_result["content"]["tables"][0])

    @staticmethod
    def build_mock_response(content):
        return BrowserResponse(
            url="https://localhost/",
            requested_url="https://localhost/",
            status_code=200,
            reason="OK",
            response_headers={"Content-Type": "text/html"},
            content=content,
            timestamp_start=datetime(1970, 1, 1),
            elapsed=timedelta(seconds=1),
        )