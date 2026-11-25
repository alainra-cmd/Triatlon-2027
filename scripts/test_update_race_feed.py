import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("update_race_feed.py")
SPEC = importlib.util.spec_from_file_location("race_feed", MODULE)
race_feed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(race_feed)

class RaceFeedTests(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(race_feed.date_from("Race 2027-06-12"), "2027-06-12")

    def test_spanish_month_date(self):
        self.assertEqual(race_feed.date_from("Triatlón el 12 de junio de 2027"), "2027-06-12")

    def test_portuguese_month_date(self):
        self.assertEqual(race_feed.date_from("Prova em 8 de maio de 2027"), "2027-05-08")

    def test_slash_date(self):
        self.assertEqual(race_feed.date_from("12/06/2027"), "2027-06-12")

    def test_reject_other_season(self):
        self.assertEqual(race_feed.date_from("2028-06-12"), "")

    def test_infer_country(self):
        self.assertEqual(race_feed.infer_country("IRONMAN in the United Kingdom"), "United Kingdom")
        self.assertEqual(race_feed.infer_country("Triatlo em Portugal"), "Portugal")

    def test_ironman_requires_european_country(self):
        source = {"id": "ironman-europe", "kind": "franchise", "country": "Europe", "name": "IRONMAN Europe", "url": "https://www.ironman.com/races"}
        self.assertIsNone(race_feed.event_obj("IRONMAN Texas", "2027-04-10", "Texas", source, source["url"], "IRONMAN", "United States"))
        self.assertIsNotNone(race_feed.event_obj("IRONMAN UK", "2027-07-10", "Bolton", source, source["url"], "IRONMAN", "United Kingdom"))

    def test_deterministic_event_ids(self):
        source = {"id": "fetri", "kind": "federation", "country": "España", "name": "FETRI", "url": "https://triatlon.org/"}
        one = race_feed.event_obj("Triatlón de prueba", "2027-06-12", "Madrid", source, source["url"], "triatlón", "Spain")
        two = race_feed.event_obj("Triatlón de prueba", "2027-06-12", "Madrid", source, source["url"], "triatlón", "Spain")
        self.assertEqual(one["id"], two["id"])

if __name__ == "__main__":
    unittest.main()
