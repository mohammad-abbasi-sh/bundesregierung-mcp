"""Live tests — hit the real www.bundesregierung.de listing and
document pages. Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set BREG_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from bundesregierung_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("BREG_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="BREG_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_press_releases_live(self):
        out = json.loads(srv.breg_press_releases(limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["section"], "pressemitteilungen")
        self.assertGreaterEqual(out["total_results"], 600)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["link"] for i in out["items"]))
        print(f"\nLIVE press releases: {out['total_results']} total, first: {out['items'][0]['title']}")

    def test_articles_live(self):
        out = json.loads(srv.breg_articles(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["total_results"], 700)
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE articles: {out['total_results']} total, first: {out['items'][0]['title']}")

    def test_speeches_live(self):
        out = json.loads(srv.breg_speeches(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["total_results"], 500)
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE speeches: {out['total_results']} total, first: {out['items'][0]['title']}")

    def test_search_live(self):
        out = json.loads(srv.breg_search("Klima", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["total_results"], 1)
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE search 'Klima': {out['total_results']} hits")

    def test_get_document_live(self):
        # A press release from the current listing: full body expected.
        listing = json.loads(srv.breg_press_releases(limit=5))
        self.assertNotIn("error", listing)
        self.assertGreater(len(listing["items"]), 0)
        link = listing["items"][0]["link"]
        out = json.loads(srv.breg_get_document(link))
        self.assertNotIn("error", out)
        self.assertEqual(out["kind"], "press-release")
        self.assertGreater(out["word_count"], 50)
        print(f"\nLIVE document: {out['word_count']} words, {out['title'][:60]}")

    def test_pagination_live(self):
        # Page 2 differs from page 1 (0-based ?page= quirk verified).
        p1 = json.loads(srv.breg_press_releases(limit=3, page=1))
        p2 = json.loads(srv.breg_press_releases(limit=3, page=2))
        self.assertNotIn("error", p1)
        self.assertNotIn("error", p2)
        self.assertNotEqual(
            p1["items"][0]["link"], p2["items"][0]["link"]
        )
        print(f"\nLIVE pagination: p1 first={p1['items'][0]['link'][-7:]}, p2 first={p2['items'][0]['link'][-7:]}")

    def test_health_live(self):
        out = json.loads(srv.breg_health())
        self.assertNotIn("error", out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)
        print(f"\nLIVE health: {out['status']}")
