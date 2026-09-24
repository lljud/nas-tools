"""Run with python -m unittest discover -s tests -p test_site_statistics.py.

Load the production model and query without initializing application services.
"""
import ast
import datetime
from pathlib import Path
import unittest

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker


ROOT = Path(__file__).resolve().parents[1]


def load_statistics_types():
    namespace = dict(vars(sa), datetime=datetime, Base=declarative_base())
    models = ast.parse((ROOT / "app/db/models.py").read_text())
    model = next(node for node in models.body
                 if isinstance(node, ast.ClassDef) and node.name == "SITESTATISTICSHISTORY")
    helper = ast.parse((ROOT / "app/helper/db_helper.py").read_text())
    cls = next(node for node in helper.body
               if isinstance(node, ast.ClassDef) and node.name == "DbHelper")
    cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                and node.name == "get_site_statistics_recent_sites"]
    module = ast.Module(body=[model, cls], type_ignores=[])
    exec(compile(module, "statistics_query", "exec"), namespace)
    return namespace["Base"], namespace["SITESTATISTICSHISTORY"], namespace["DbHelper"]


Base, History, DbHelper = load_statistics_types()


class TestSiteStatistics(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.helper = DbHelper()
        self.helper._db = self.session

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def add(self, day, upload, download, site="test", url="test.example"):
        self.session.add(History(SITE=site, DATE=day, UPLOAD=str(upload),
                                 DOWNLOAD=str(download), URL=url))
        self.session.flush()

    def query(self, days, **kwargs):
        # Match the web action's extra baseline day.
        return self.helper.get_site_statistics_recent_sites(
            days=days + 1, end_day="2026-09-24", **kwargs)

    def test_old_zero_snapshot_does_not_erase_month_and_year(self):
        self.add("2026-09-01", 100, 50)
        self.add("2026-09-11", 0, 0)
        self.add("2026-09-17", 140, 60)
        self.add("2026-09-23", 160, 70)
        self.add("2026-09-24", 180, 80)
        for days, expected in [(1, (20, 10)), (7, (40, 20)),
                               (30, (80, 30)), (365, (80, 30))]:
            with self.subTest(days=days):
                self.assertEqual(self.query(days), (*expected, ["test"],
                                                   [expected[0]], [expected[1]]))

    def test_zero_download_is_valid(self):
        self.add("2026-09-23", 100, 0)
        self.add("2026-09-24", 180, 30)
        self.assertEqual(self.query(1)[:2], (80, 30))

    def test_zero_upload_is_valid(self):
        self.add("2026-09-23", 0, 50)
        self.add("2026-09-24", 180, 80)
        self.assertEqual(self.query(1)[:2], (180, 30))

    def test_all_zero_snapshots(self):
        self.add("2026-09-23", 0, 0)
        self.add("2026-09-24", 0, 0)
        self.assertEqual(self.query(30), (0, 0, ["test"], [0], [0]))

    def test_single_valid_snapshot_has_no_known_increment(self):
        self.add("2026-09-23", 0, 0)
        self.add("2026-09-24", 180, 80)
        self.assertEqual(self.query(30), (0, 0, ["test"], [0], [0]))

    def test_empty_history(self):
        self.assertEqual(self.query(30), (0, 0, [], [], []))

    def test_date_bounds_and_site_filter(self):
        self.add("2026-09-22", 1, 1)
        self.add("2026-09-23", 100, 50)
        self.add("2026-09-24", 180, 80)
        self.add("2026-09-25", 1000, 1000)
        self.add("2026-09-23", 1, 1, site="other", url="other.example")
        self.add("2026-09-24", 9999, 9999, site="other", url="other.example")
        self.assertEqual(self.query(1, strict_urls=["test.example"]),
                         (80, 30, ["test"], [80], [30]))
        self.assertEqual(self.query(30, strict_urls=["missing.example"]),
                         (0, 0, [], [], []))


if __name__ == "__main__":
    unittest.main()
