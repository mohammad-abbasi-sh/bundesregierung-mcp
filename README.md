# bundesregierung-mcp 🇩🇪

mcp-name: io.github.mohammad-abbasi-sh/bundesregierung-mcp

Unofficial **read-only** MCP server for **[bundesregierung.de](https://www.bundesregierung.de)** — the German federal government's official site — via its listing pages (press releases, articles / Meldungen, speeches & press conferences) and document pages, whose full text is read from the server-rendered reading area. Latest press releases (612 at last check), articles (732) and speeches (567), newest first, keyword search across the whole site, and full document text — some press releases also carry the official English translation inline. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with the German federal government or the Presse- und Informationsamt der Bundesregierung.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "bundesregierung": {
      "command": "uvx",
      "args": ["bundesregierung-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m bundesregierung_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `breg_press_releases` | Latest press releases (Pressemitteilungen) of the German federal government, newest first — `limit` 1..50, `page` 1-based. Items carry title, topline, link, type, publish time (press-release teasers carry no description) |
| `breg_articles` | Latest articles / Meldungen, newest first — `limit` 1..50, `page` 1-based. Items carry title, topline, link, publish time and a short description |
| `breg_speeches` | Latest speeches, press statements and press conferences (Pressekonferenzen und Reden), newest first — mostly full transcripts ("Im Wortlaut") — `limit` 1..50, `page` 1-based |
| `breg_search` | Search bundesregierung.de by keyword across the whole site (press releases, articles, speeches) — `query` (e.g. "Klima"), `limit` 1..50, `page` 1-based. Items link via a /breg-de/suche/ alias URL |
| `breg_get_document` | Full text of one document — press release, article or speech/transcript — `url`: a www.bundesregierung.de document URL (/breg-de/aktuelles/... or a /breg-de/suche/ alias). Returns title, publish time, kind, the German body + word count, and `body_en` with the official English translation when the site carries one inline |
| `breg_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`breg_press_releases`, `limit` 1):

```json
{"section": "pressemitteilungen", "total_results": 612, "page_count": 62, "page": 1, "count": 1,
 "items": [
  {"title": "Erklärung von Bundeskanzler Friedrich Merz zum Mehrjährigen Finanzrahmen 2028-2034",
   "topline": null,
   "link": "https://www.bundesregierung.de/breg-de/aktuelles/pressemitteilungen/erklaerung-von-bundeskanzler-friedrich-merz-zum-mehrjaehrigen-finanzrahmen-2028-2034-2462246",
   "type": "Pressemitteilung",
   "published": "2026-11-21T12:25:00Z",
   "description": null}]}
```

Notes:
- The server reads the site's **listing pages** (`/breg-de/aktuelles/{pressemitteilungen,artikel,pressekonferenzen-und-reden}`, verified live 2026-11-22). The results are embedded server-side as `BPA.initialSearchResultsJson` in the HTML — there is **no RSS feed**: `/breg-de/service/rss-feeds` 404s and the pages carry no `<link rel="alternate">` feed.
- **Pagination quirk, verified live:** the site's `?page=` is 0-based — `?page=N` returns page N+1. Page 1 carries 11 items, later pages 10. Listing tools fetch successive pages until the requested `limit` is met.
- **Document text, honestly:** the full text is read from the server-rendered `#rs_reading_area_content` paragraphs (statement: 7 German + 8 English paragraphs incl. heading, 249 / 306 words; speech transcript: 20 paragraphs, 1,113 words; article: 11 paragraphs, 577 words — all sampled live). Article pages mix in an image caption + "Foto:" credit line and trailing related-link lines ("Pressemitteilung des BMDS: ..."); all three are filtered out of the body.
- **English translations:** some press releases carry the official English translation inline (`lang="en-GB"` spans wrapping whole paragraphs) — it is returned separately as `body_en` (`has_english_translation: true`). Inline foreign words (e.g. "EUDI-Wallet") are also marked `lang="en-GB"` but are single words, so a segment counts as English only when the en-GB spans cover ≥ 50% of its text.
- **Speech dates, honestly:** speech/transcript pages ("Mitschrift Pressekonferenz") carry NO `<time datetime>` — their date is read from the header's German date line ("Freitag, 20. November 2026" → `2026-11-20`). The featured (image) teaser on the article listing likewise carries no `<time>` — its date falls back to the item's `sortDate` field (site-local time, no offset).
- Data: bundesregierung.de public listing and document pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the three real captured listing pages (press releases, articles, site search) plus three real document pages (a press-release statement with English translation, an article, a speech transcript)
- `tests/test_live.py` — cautious live requests against www.bundesregierung.de

Tests: 29/29 green (22 offline + 7 live, 2026-11-22).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
