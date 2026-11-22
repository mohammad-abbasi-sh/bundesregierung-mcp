"""MCP server: unofficial read-only access to bundesregierung.de —
the German federal government's official site — via its listing
pages (press releases, articles, speeches/press conferences) and
document pages (full text, incl. the official English translation
when the site carries one inline).
No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for bundesregierung.de — the German
federal government's official site (no key, no login). Latest press
releases (612 at last check), articles / Meldungen (732) and
speeches & press conferences (567), newest first, with title,
topline, type, publish time and link; keyword search across the
whole site; and the full text of any press release, article or
speech (server-rendered body — some press releases also carry the
official English translation inline, returned separately as
body_en). NOTE: the site has NO RSS feed (/breg-de/service/rss-feeds
404s) — listings come from the results JSON the site embeds
server-side in each listing page. Speech/transcript pages carry no
machine-readable publish time; their date is read from the header's
German date line when present. Built by Mohammad Abbasi
(mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir
— Germany MCP factory.\
"""


_SOURCE = "www.bundesregierung.de"
_DISCLAIMER = "Unofficial read-only data from bundesregierung.de's public listing and document pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("bundesregierung-mcp", instructions=INSTRUCTIONS)


def _listing(section: str, limit: int, page: int) -> dict:
    """Fetch listing pages from ``page`` onward until ``limit``
    items are collected (page 1 carries 11 items, later pages 10)."""
    items: list[dict] = []
    total = None
    page_count = None
    cur = page
    while len(items) < limit:
        html_text, _url = _http.fetch_listing(section, cur)
        parsed = _dom.parse_listing(html_text)
        total = parsed["total_results"]
        page_count = parsed["page_count"]
        items.extend(parsed["items"])
        if page_count is None or cur >= page_count:
            break
        cur += 1
    return {
        "section": section,
        "total_results": total,
        "page_count": page_count,
        "page": page,
        "count": min(limit, len(items)),
        "items": items[:limit],
    }


def _search(query: str, limit: int, page: int) -> dict:
    """Fetch site-search pages from ``page`` onward until ``limit``
    items are collected."""
    items: list[dict] = []
    total = None
    page_count = None
    cur = page
    while len(items) < limit:
        html_text, _url = _http.fetch_search(query, cur)
        parsed = _dom.parse_listing(html_text)
        total = parsed["total_results"]
        page_count = parsed["page_count"]
        items.extend(parsed["items"])
        if page_count is None or cur >= page_count:
            break
        cur += 1
    return {
        "query": query,
        "total_results": total,
        "page_count": page_count,
        "page": page,
        "count": min(limit, len(items)),
        "items": items[:limit],
    }


@mcp.tool()
def breg_press_releases(limit: int = 10, page: int = 1) -> str:
    """Latest press releases (Pressemitteilungen) of the German
    federal government, newest first. limit: 1..50 (default 10);
    page: 1-based starting page (default 1). Items carry title,
    topline, link (a per-document URL for breg_get_document), type,
    publish time and — for press releases — no description (the
    teasers carry title + date only)."""
    try:
        lim = _dom.validate_limit(limit)
        pg = _dom.validate_page(page)
        out = _listing("pressemitteilungen", lim, pg)
    except (_http.BregError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def breg_articles(limit: int = 10, page: int = 1) -> str:
    """Latest articles / Meldungen from bundesregierung.de, newest
    first. limit: 1..50 (default 10); page: 1-based starting page
    (default 1). Items carry title, topline, link (a per-document
    URL for breg_get_document), publish time and a short
    description."""
    try:
        lim = _dom.validate_limit(limit)
        pg = _dom.validate_page(page)
        out = _listing("artikel", lim, pg)
    except (_http.BregError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def breg_speeches(limit: int = 10, page: int = 1) -> str:
    """Latest speeches, press statements and press conferences
    (Pressekonferenzen und Reden) of the German federal
    government, newest first — mostly full transcripts ("Im
    Wortlaut"). limit: 1..50 (default 10); page: 1-based starting
    page (default 1). Items carry title, topline, link (a
    per-document URL for breg_get_document), type and publish
    time."""
    try:
        lim = _dom.validate_limit(limit)
        pg = _dom.validate_page(page)
        out = _listing("pressekonferenzen-und-reden", lim, pg)
    except (_http.BregError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def breg_search(query: str, limit: int = 10, page: int = 1) -> str:
    """Search bundesregierung.de by keyword across the whole site
    (press releases, articles, speeches). query: free text, e.g.
    "Klima" or "Bundeshaushalt 2027". limit: 1..50 (default 10);
    page: 1-based starting page (default 1). Items carry title,
    topline, link (a /breg-de/suche/ alias URL — breg_get_document
    follows it to the canonical document), publish time and a short
    description."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        pg = _dom.validate_page(page)
        out = _search(query.strip(), lim, pg)
    except (_http.BregError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def breg_get_document(url: str) -> str:
    """Full text of one bundesregierung.de document — a press
    release, article or speech/transcript. url: a
    www.bundesregierung.de document URL, e.g. from
    breg_press_releases (/breg-de/aktuelles/pressemitteilungen/...)
    or a /breg-de/suche/<slug>-<id> alias from breg_search (it
    redirects to the canonical document). Returns title, publish
    time, kind (press-release / article / speech / document), the
    German body text and its word count, plus body_en with the
    official English translation when the site carries one inline
    (has_english_translation). Speech pages carry no
    machine-readable publish time — their date is read from the
    header's German date line when present. Nothing is ever
    fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        html_text, final_url = _http.fetch_document(url)
        doc = _dom.parse_document(html_text, final_url)
        note = ""
        if doc["has_english_translation"]:
            note = (
                "This document also carries the official English "
                "translation inline (body_en)."
            )
        elif doc["kind"] == "speech" and not doc["published"]:
            note = (
                "Speech/transcript pages carry no machine-readable "
                "publish time; use the listing date for this document."
            )
        out = {
            "url": final_url,
            "requested_url": url,
            "title": doc["title"],
            "published": doc["published"],
            "kind": doc["kind"],
            "word_count": doc["word_count"],
            "body": doc["body"],
            "has_english_translation": doc["has_english_translation"],
            "body_en": doc["body_en"],
            "word_count_en": doc["word_count_en"],
            "note": note,
        }
    except (_http.BregError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def breg_health() -> str:
    """Check whether the bundesregierung.de press-releases listing
    is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
