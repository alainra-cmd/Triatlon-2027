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

    def test_month_first_english_date(self):
        self.assertEqual(race_feed.date_from("IRONMAN 70.3 — April 3, 2027, Vilamoura"), "2027-04-03")

    def test_abbreviated_month_date(self):
        self.assertEqual(race_feed.date_from("17 Apr 2027 08:00"), "2027-04-17")

    def test_challenge_calendar_card(self):
        from bs4 import BeautifulSoup
        source = {"id":"challenge-europe","name":"Challenge Family · Europa","country":"Europe","kind":"franchise","url":"https://challengefamily.com/races/?_continent=europe"}
        html = """<h2>Anfi Challenge</h2><h2>Mogán-Gran Canaria</h2><h3>100 distance, Standard distance</h3><h3>17 Apr 2027 08:00</h3><h3>Gran Canaria, Spain</h3>"""
        events = race_feed.parse_challenge_calendar(BeautifulSoup(html,"html.parser"),source,source["url"])
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["name"],"Mogán-Gran Canaria")
        self.assertEqual(events[0]["date"],"2027-04-17")
        self.assertEqual(events[0]["place"],"Gran Canaria")

    def test_ironman_directory_card(self):
        from bs4 import BeautifulSoup
        source = {"id":"ironman-directory","name":"IRONMAN directory","country":"Europe","kind":"supplemental","url":"https://findmytris.com/races/continent/europe"}
        html = """<ul><li><a href="/race/vilamoura">IRONMAN 70.3 Vilamoura-Algarve</a> — April 3, 2027, Vilamoura, Portugal · IRONMAN 70.3</li></ul>"""
        events = race_feed.parse_ironman_directory(BeautifulSoup(html,"html.parser"),source,source["url"])
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["date"],"2027-04-03")
        self.assertEqual(events[0]["country"],"Portugal")
        self.assertEqual(events[0]["franchise"],"IRONMAN")

    def test_fetri_calendar_has_confirmed_events(self):
        source = {"id":"fetri-2027-calendar","name":"FETRI 2027","country":"Spain","kind":"federation","url":"https://triatlon.org/noticias/fetri-lanza-el-calendario-de-competiciones-nacionales-e-internacionales-en-el-ano-2027/"}
        events = race_feed.parse_fetri_2027(source)
        self.assertGreaterEqual(len(events),25)
        self.assertTrue(any("Banyoles" in x["name"] for x in events))

    def test_training_course_is_not_a_race(self):
        source = {"id":"fetri","name":"FETRI","country":"Spain","kind":"federation","url":"https://triatlon.org/"}
        self.assertIsNone(race_feed.event_obj("Curso Oficial Técnico de Triatlón FETRI Nivel 1 - 2027","2027-01-09","Madrid",source,source["url"],"triatlón"))

    def test_catalan_federation_calendar_table(self):
        from bs4 import BeautifulSoup
        source = {"id":"cataluna","name":"Federació Catalana","country":"España","kind":"regional","url":"https://www.triatlo.org/competicions/?idany=2027&oficial=0"}
        html = """<table><tr><th>DATA</th><th>NOM</th><th>TIPUS</th><th>POBLACIÓ</th></tr><tr><td>17/01/2027</td><td>XVII DUATLÓ DE GRANOLLERS</td><td>Duatló de Carretera</td><td>MONTMELÓ</td></tr></table>"""
        events = race_feed.extract_tables(BeautifulSoup(html,"html.parser"),source,source["url"])
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["name"],"XVII DUATLÓ DE GRANOLLERS")
        self.assertEqual(events[0]["place"],"MONTMELÓ")

if __name__ == "__main__":
    unittest.main()
