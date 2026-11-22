"""Offline tests — recorded fixtures from www.bundesregierung.de
(listings captured 2026-11-22; see tests/fixtures/).

Run:  pytest tests/test_domain.py -v
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from bundesregierung_mcp import domain as d

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class TestListingPressReleases(unittest.TestCase):
    def setUp(self):
        self.parsed = d.parse_listing(_read("listing-pressemitteilungen.html"))

    def test_counts(self):
        self.assertEqual(self.parsed["total_results"], 612)
        self.assertEqual(self.parsed["page"], 1)
        self.assertEqual(self.parsed["page_count"], 62)
        self.assertEqual(self.parsed["count"], 11)

    def test_first_item(self):
        first = self.parsed["items"][0]
        self.assertEqual(
            first["title"],
            "Erklärung von Bundeskanzler Friedrich Merz zum "
            "Mehrjährigen Finanzrahmen 2028-2034",
        )
        self.assertEqual(
            first["link"],
            "https://www.bundesregierung.de/breg-de/aktuelles/"
            "pressemitteilungen/erklaerung-von-bundeskanzler-"
            "friedrich-merz-zum-mehrjaehrigen-finanzrahmen-2028-2034-2462246",
        )
        self.assertEqual(first["type"], "Pressemitteilung")
        self.assertEqual(first["published"], "2026-11-21T12:25:00Z")
        self.assertIsNone(first["description"])  # PM teasers: no teaser text
        self.assertIsNone(first["topline"])

    def test_all_items_have_title_link_date(self):
        for item in self.parsed["items"]:
            self.assertTrue(item["title"])
            self.assertTrue(item["link"].startswith("https://www.bundesregierung.de/"))
            self.assertTrue(item["published"])


class TestListingArticles(unittest.TestCase):
    def setUp(self):
        self.parsed = d.parse_listing(_read("listing-artikel.html"))

    def test_counts(self):
        self.assertEqual(self.parsed["total_results"], 732)
        self.assertEqual(self.parsed["page_count"], 74)
        self.assertEqual(self.parsed["count"], 11)

    def test_first_item_featured_teaser(self):
        # The featured (image) teaser carries no <time> in its
        # payload — its date falls back to the sortDate field.
        first = self.parsed["items"][0]
        self.assertEqual(first["title"], "Die digitale Brieftasche kommt")
        self.assertEqual(first["topline"], "Bundesrat stimmt zu")
        self.assertEqual(
            first["link"],
            "https://www.bundesregierung.de/breg-de/aktuelles/"
            "digitale-brieftasche-2431500",
        )
        self.assertEqual(first["published"], "2026-11-20T15:00:00")
        self.assertTrue(
            (first["description"] or "").startswith(
                "Mit dem Digitale Identitätengesetz"
            )
        )

    def test_second_item_has_time(self):
        second = self.parsed["items"][1]
        self.assertEqual(second["published"], "2026-11-20T13:00:00Z")


class TestListingSearch(unittest.TestCase):
    def setUp(self):
        self.parsed = d.parse_listing(_read("listing-search.html"))

    def test_counts(self):
        self.assertEqual(self.parsed["total_results"], 190)
        self.assertEqual(self.parsed["page_count"], 19)
        self.assertEqual(self.parsed["count"], 11)

    def test_first_item_search_alias_link(self):
        first = self.parsed["items"][0]
        self.assertEqual(first["topline"], "Bundeshaushalt 2027")
        self.assertEqual(
            first["title"], "Etat im Zeichen von Wohlstand und Sicherheit"
        )
        self.assertEqual(
            first["link"],
            "https://www.bundesregierung.de/breg-de/suche/"
            "bundeshaushalt-2027-2446026",
        )
        self.assertEqual(first["published"], "2026-11-13T11:45:00Z")
        self.assertTrue(
            (first["description"] or "").startswith(
                "Die Bundesregierung hat den Entwurf für den Bundeshaushalt 2027"
            )
        )


class TestListingErrors(unittest.TestCase):
    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            d.parse_listing("<html><body>not a listing</body></html>")

    def test_validate_limit(self):
        self.assertEqual(d.validate_limit(50), 50)
        with self.assertRaises(ValueError):
            d.validate_limit(0)
        with self.assertRaises(ValueError):
            d.validate_limit(51)

    def test_validate_page(self):
        self.assertEqual(d.validate_page(1), 1)
        with self.assertRaises(ValueError):
            d.validate_page(0)

    def test_validate_section(self):
        self.assertEqual(d.validate_section("Artikel"), "artikel")
        with self.assertRaises(ValueError):
            d.validate_section("bundestag")

    def test_urls(self):
        self.assertEqual(
            d.listing_url("pressemitteilungen", 1),
            "https://www.bundesregierung.de/breg-de/aktuelles/"
            "pressemitteilungen?page=0",
        )
        self.assertEqual(
            d.listing_url("pressemitteilungen", 3),
            "https://www.bundesregierung.de/breg-de/aktuelles/"
            "pressemitteilungen?page=2",
        )
        self.assertEqual(
            d.search_url("Klima", 1),
            "https://www.bundesregierung.de/breg-de/suche/"
            "992800!search?query=Klima&page=0",
        )
        self.assertEqual(
            d.search_url("Bundeshaushalt 2027", 2),
            "https://www.bundesregierung.de/breg-de/suche/"
            "992800!search?query=Bundeshaushalt%202027&page=1",
        )


class TestDocumentStatement(unittest.TestCase):
    URL = (
        "https://www.bundesregierung.de/breg-de/aktuelles/"
        "pressemitteilungen/erklaerung-von-bundeskanzler-"
        "friedrich-merz-zum-mehrjaehrigen-finanzrahmen-2028-2034-2462246"
    )

    def setUp(self):
        self.doc = d.parse_document(_read("document-statement.html"), self.URL)

    def test_meta(self):
        self.assertEqual(
            self.doc["title"],
            "Erklärung von Bundeskanzler Friedrich Merz zum "
            "Mehrjährigen Finanzrahmen 2028-2034",
        )
        self.assertEqual(self.doc["published"], "2026-11-21T12:25:00Z")
        self.assertEqual(self.doc["kind"], "press-release")

    def test_german_body(self):
        self.assertEqual(len(self.doc["body"].split("\n\n")), 7)
        self.assertTrue(
            self.doc["body"].startswith(
                "Seit Beginn der Verhandlungen vor mehr als einem Jahr"
            )
        )
        self.assertTrue(
            self.doc["body"].endswith(
                "Ein Abschluss in 2026 ist im Interesse von uns allen in Europa."
            )
        )
        self.assertEqual(self.doc["word_count"], 249)

    def test_english_translation(self):
        self.assertTrue(self.doc["has_english_translation"])
        self.assertEqual(len(self.doc["body_en"].split("\n\n")), 8)
        self.assertTrue(
            self.doc["body_en"].startswith(
                "Statement by Chancellor Friedrich Merz on the "
                "Multiannual Financial Framework 2028–2034"
            )
        )
        self.assertEqual(self.doc["word_count_en"], 306)


class TestDocumentArticle(unittest.TestCase):
    URL = (
        "https://www.bundesregierung.de/breg-de/aktuelles/"
        "digitale-brieftasche-2431500"
    )

    def setUp(self):
        self.doc = d.parse_document(_read("document-artikel.html"), self.URL)

    def test_meta(self):
        self.assertEqual(self.doc["title"], "Die digitale Brieftasche kommt")
        self.assertEqual(self.doc["published"], "2026-11-20T14:00:00Z")
        self.assertEqual(self.doc["kind"], "article")
        self.assertFalse(self.doc["has_english_translation"])
        self.assertEqual(self.doc["body_en"], "")

    def test_body_filters(self):
        # Image caption + "Foto:" credit + trailing related-link
        # lines are filtered out; the Q&A body paragraphs stay.
        self.assertEqual(len(self.doc["body"].split("\n\n")), 11)
        self.assertNotIn("Foto:", self.doc["body"])
        self.assertNotIn("Bundesdigitalminister Wildberger bei der Präsentation", self.doc["body"])
        self.assertNotIn("Pressemitteilung des BMDS", self.doc["body"])
        self.assertIn("Die digitale Brieftasche kann kommen", self.doc["body"])
        self.assertIn("Nein. Die Wallet wird kostenlos", self.doc["body"])
        self.assertEqual(self.doc["word_count"], 577)


class TestDocumentSpeech(unittest.TestCase):
    URL = (
        "https://www.bundesregierung.de/breg-de/aktuelles/"
        "pressestatements-von-bundeskanzler-merz-und-emir-tamim-"
        "bin-hamad-al-thani-zum-besuch-des-emirs-in-deutschland-"
        "am-20-november-2026-2462202"
    )

    def setUp(self):
        self.doc = d.parse_document(_read("document-speech.html"), self.URL)

    def test_meta(self):
        self.assertEqual(
            self.doc["title"],
            "Pressestatements von Bundeskanzler Merz und Emir Tamim "
            "bin Hamad Al Thani zum Besuch des Emirs in Deutschland "
            "am 20. November 2026",
        )
        # Speech pages carry no <time> — the date comes from the
        # header's German date line.
        self.assertEqual(self.doc["published"], "2026-11-20")
        self.assertEqual(self.doc["kind"], "speech")
        self.assertFalse(self.doc["has_english_translation"])

    def test_transcript_body(self):
        self.assertEqual(len(self.doc["body"].split("\n\n")), 20)
        self.assertTrue(self.doc["body"].startswith("Bundeskanzler Merz"))
        self.assertIn(
            "Eure königliche Hoheit, Emir Al Thani", self.doc["body"]
        )
        self.assertIn("Vielen Dank, Herr Bundeskanzler.", self.doc["body"])
        self.assertEqual(self.doc["word_count"], 1113)


class TestDocumentErrors(unittest.TestCase):
    def test_no_reading_area_raises(self):
        with self.assertRaises(ValueError):
            d.parse_document(
                "<html><body>no article here</body></html>",
                "https://www.bundesregierung.de/breg-de/aktuelles/x-1",
            )

    def test_kind_of_url(self):
        self.assertEqual(
            d.kind_of_url(
                "https://www.bundesregierung.de/breg-de/aktuelles/"
                "pressemitteilungen/x-1"
            ),
            "press-release",
        )
        self.assertEqual(
            d.kind_of_url(
                "https://www.bundesregierung.de/breg-de/aktuelles/x-1"
            ),
            "article",
        )
        self.assertEqual(
            d.kind_of_url(
                "https://www.bundesregierung.de/breg-de/suche/x-1"
            ),
            "document",
        )


if __name__ == "__main__":
    unittest.main()
