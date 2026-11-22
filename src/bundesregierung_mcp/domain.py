"""Domain logic: shape bundesregierung.de (the German federal
government's official site) into compact dicts (stdlib only).

Data source: the site's own listing pages, whose results are
embedded server-side as ``BPA.initialSearchResultsJson`` (a JSON
blob in the HTML — no key, no login), plus the document pages,
whose full text lives in the server-rendered
``#rs_reading_area_content`` paragraphs.

Honest limitations (verified live 2026-11-22):
- There is NO RSS feed: /breg-de/service/rss-feeds 404s, and the
  listing pages carry no <link rel="alternate"> feed. Listings
  come from the embedded search JSON (612 press releases, 732
  articles, 567 speeches/press conferences at last check).
- Pagination is 0-based: ?page=N returns page N+1. Page 1 carries
  11 items, later pages 10. Listing tools therefore fetch
  successive pages until the requested limit is met.
- Press-release teasers carry no description text (title + type +
  date only); article and search teasers carry a short text. The
  featured (image) teaser on the article listing carries no
  <time> in its payload — its date falls back to the item's
  sortDate field (site-local time, no offset; the <time> value,
  when present, is UTC).
- Document pages carry the full text in #rs_reading_area_content
  <p> blocks, paragraphs separated by <br/> runs inside a single
  <p> on statement/speech pages (single and double <br/> both
  occur) and as separate <p> blocks on article pages. Some press
  releases include the official English translation inline
  (lang="en-GB" spans wrapping whole paragraphs); it is returned
  separately as body_en when present.
  Inline foreign words (e.g. "EUDI-Wallet") are also marked
  lang="en-GB" but are single words, so a segment counts as
  English only when the en-GB spans cover >= 50% of its text.
- Speech/transcript pages ("Mitschrift Pressekonferenz") carry NO
  <time datetime> — the date is read from the header's German date
  line ("Freitag, 20. November 2026") and returned as a plain
  date; article/press-release pages carry a full <time datetime>.
- Article pages mix in an image caption + "Foto:" credit line and
  trailing related-link lines ("Pressemitteilung des BMDS: ...");
  all three are filtered out of the body.
"""
from __future__ import annotations

import html
import json
import re
from urllib.parse import quote, urlparse

BASE = "https://www.bundesregierung.de"

# Listing sections under /breg-de/aktuelles/ — counts at last live
# check (2026-11-22): press releases 612, articles 732,
# speeches/press conferences 567.
SECTIONS = (
    "pressemitteilungen",
    "artikel",
    "pressekonferenzen-und-reden",
)
SEARCH_PAGE_ID = "992800"

# Page sizes observed live: 11 items on page 1, 10 on later pages.
_FIRST_PAGE_SIZE = 11
_PAGE_SIZE = 10

_MONTHS_DE = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5,
    "Juni": 6, "Juli": 7, "August": 8, "September": 9,
    "Oktober": 10, "November": 11, "Dezember": 12,
}


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (listings carry ~10 items/page)."""
    if not 1 <= limit <= 50:
        raise ValueError(f"limit out of range: {limit} (expected 1..50)")
    return limit


def validate_page(page: int) -> int:
    """Validate the 1-based starting page."""
    if not 1 <= page <= 200:
        raise ValueError(f"page out of range: {page} (expected 1..200)")
    return page


def validate_section(section: str) -> str:
    """Normalise a listing section name."""
    s = (section or "").strip().casefold()
    if s not in SECTIONS:
        raise ValueError(
            f"unknown section: {section!r} (available: {', '.join(SECTIONS)})"
        )
    return s


def listing_url(section: str, page: int) -> str:
    """Listing URL for 1-based page ``page`` (the site's ?page= is
    0-based: ?page=N returns page N+1)."""
    return f"{BASE}/breg-de/aktuelles/{section}?page={page - 1}"


def search_url(query: str, page: int) -> str:
    """Site-search URL for 1-based page ``page`` (same 0-based
    ?page= quirk as the listings)."""
    return (
        f"{BASE}/breg-de/suche/{SEARCH_PAGE_ID}!search"
        f"?query={quote(query)}&page={page - 1}"
    )


def _extract_listing_json(html_text: str) -> dict:
    """Pull the BPA.initialSearchResultsJson blob out of a listing
    page (brace-balanced scan, so payload HTML inside the JSON
    cannot cut the match short). Raises ValueError when the blob
    is missing or unparsable."""
    marker = "BPA.initialSearchResultsJson"
    start = html_text.find(marker)
    if start < 0:
        raise ValueError(
            "no search results found on this page (the embedded "
            "results JSON is missing) — the page may be an error "
            "page or the site layout may have changed"
        )
    brace = html_text.find("{", start)
    if brace < 0:
        raise ValueError("no search results found on this page")
    depth = 0
    in_str = False
    esc = False
    for i in range(brace, len(html_text)):
        ch = html_text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html_text[brace:i + 1])
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"invalid results JSON on this page: {e}"
                    ) from e
    raise ValueError("unterminated results JSON on this page")


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw or "")
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


_TITLE_RE = re.compile(
    r'bpa-teaser-title-text-inner"[^>]*>(.*?)</span>', re.S | re.I
)
_TOPLINE_RE = re.compile(
    r'bpa-topline-title"[^>]*>(.*?)</span>', re.S | re.I
)
_LINK_RE = re.compile(r'href="(https://www\.bundesregierung\.de[^"]+)"')
_TIME_RE = re.compile(r'<time datetime="([^"]+)"')
_INFO_RE = re.compile(
    r'bpa-teaser-info"[^>]*>(.*?)<span class="bpa-dash"', re.S | re.I
)
_SHORT_RE = re.compile(
    r'<p class="bpa-short-text"[^>]*>(.*?)</p>', re.S | re.I
)


def compact_item(payload: str, sort_date: str | None = None) -> dict:
    """One listing teaser (the payload HTML of one search-result
    item): title, topline, link, type, publish time, description.

    The publish time comes from the payload's <time datetime>
    (UTC) when present; the featured image teaser carries none, so
    its sortDate (site-local time) is the fallback."""
    link_m = _LINK_RE.search(payload)
    link = link_m.group(1) if link_m else ""
    title_m = _TITLE_RE.search(payload)
    title = _strip_tags(title_m.group(1)) if title_m else ""
    topline_m = _TOPLINE_RE.search(payload)
    topline = _strip_tags(topline_m.group(1)) if topline_m else None
    time_m = _TIME_RE.search(payload)
    published = time_m.group(1) if time_m else sort_date
    info_m = _INFO_RE.search(payload)
    kind = _strip_tags(info_m.group(1)) if info_m else None
    kind = kind or None
    short_m = _SHORT_RE.search(payload)
    description = _strip_tags(short_m.group(1)) if short_m else None
    return {
        "title": title,
        "topline": topline,
        "link": link,
        "type": kind,
        "published": published,
        "description": description,
    }


def parse_listing(html_text: str) -> dict:
    """Parse a listing/search page into {total_results, page,
    page_count, count, items}. Raises ValueError on a page without
    the embedded results JSON."""
    data = _extract_listing_json(html_text)
    result = data.get("result") or {}
    items = [
        compact_item(it.get("payload") or "", it.get("sortDate"))
        for it in result.get("items") or []
    ]
    return {
        "total_results": result.get("count"),
        "page": result.get("page"),
        "page_count": result.get("pageCount"),
        "count": len(items),
        "items": items,
    }


def kind_of_url(url: str, html_text: str = "") -> str:
    """Document kind: the page header's collection list names the
    type ("Pressemitteilung 208", "Mitschrift Pressekonferenz")
    when present; otherwise the URL path decides. Speech listings
    link straight to /breg-de/aktuelles/<slug>-<id> (the same shape
    as articles), so the URL alone cannot tell them apart."""
    if html_text:
        for m in _COLLECTION_RE.finditer(html_text):
            text = _strip_tags(m.group(1))
            if any(w in text for w in ("Pressekonferenz", "Mitschrift", "Rede")):
                return "speech"
            if "Pressemitteilung" in text:
                return "press-release"
    try:
        path = urlparse(url).path
    except ValueError:
        return "document"
    if "/pressemitteilungen/" in path:
        return "press-release"
    if "/pressekonferenzen-und-reden/" in path:
        return "speech"
    if path.startswith("/breg-de/aktuelles/"):
        return "article"
    return "document"


_TITLE_TAG_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_PARA_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
_BR_RUN_RE = re.compile(r"(?:<br\s*/?>\s*)+", re.I)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_EN_SPAN_RE = re.compile(
    r'<span[^>]*lang="en-GB"[^>]*>(.*?)</span>', re.S | re.I
)
_COLLECTION_RE = re.compile(
    r'<li class="bpa-collection-item"[^>]*>(.*?)</li>', re.S | re.I
)
_DE_DATE_RE = re.compile(
    r"(\d{1,2})\.\s*"
    r"(Januar|Februar|März|April|Mai|Juni|Juli|August|September|"
    r"Oktober|November|Dezember)\s*(\d{4})"
)

_DROP_PREFIXES = (
    "Foto:",
    "Text vorlesen ist nicht aktiviert",
    "Die Audioversion wurde künstlich erzeugt.",
)


def _is_english_segment(raw_html: str, text: str) -> bool:
    """True when the lang="en-GB" spans cover >= 50% of the
    segment's text — whole translated paragraphs, not inline
    foreign words (which are a few characters long)."""
    if not text:
        return False
    en_len = 0
    for m in _EN_SPAN_RE.finditer(raw_html):
        en_len += len(_strip_tags(m.group(1)))
    return en_len * 2 >= len(text)


def _header_date(html_text: str) -> str | None:
    """German date line from the article header ("Freitag, 20.
    November 2026" in a bpa-collection-item) as ISO YYYY-MM-DD.
    Used when the page carries no <time datetime> (speech pages)."""
    for m in _COLLECTION_RE.finditer(html_text):
        text = _strip_tags(m.group(1))
        dm = _DE_DATE_RE.search(text)
        if dm:
            day, month, year = dm.groups()
            return f"{year}-{_MONTHS_DE[month]:02d}-{int(day):02d}"
    return None


def _content_region(html_text: str) -> str:
    """The #rs_reading_area_content region, cut before the footer
    so no footer <p> blocks leak into the body."""
    start = html_text.find('id="rs_reading_area_content"')
    if start < 0:
        raise ValueError(
            "no document text found on this page (no reading-area "
            "content) — the page may be a video/landing page or an "
            "error page"
        )
    region = html_text[start:]
    cuts = [
        region.find(marker)
        for marker in ("<footer", "SERVICES DER BUNDESREGIERUNG")
    ]
    cuts = [c for c in cuts if c > 0]
    if cuts:
        region = region[:min(cuts)]
    return region


def parse_document(html_text: str, url: str) -> dict:
    """Extract a bundesregierung.de document page.

    Returns {title, published, kind, body, body_en,
    has_english_translation, word_count, word_count_en}.
    Raises ValueError when no usable text is found.
    """
    title_m = _TITLE_TAG_RE.search(html_text)
    title = _strip_tags(title_m.group(1)) if title_m else ""
    title = re.sub(r"\s*\|\s*Bundesregierung\s*$", "", title)
    time_m = _TIME_RE.search(html_text)
    published = time_m.group(1) if time_m else _header_date(html_text)

    region = _content_region(html_text)
    raw_paras = _PARA_RE.findall(region)

    # Drop the image caption (the <p> right before a "Foto:" credit
    # line), the credit line itself, boilerplate lines and trailing
    # related-link lines ("Pressemitteilung des BMDS: ...").
    kept: list[str] = []
    for i, raw in enumerate(raw_paras):
        text = _strip_tags(raw)
        if not text:
            continue
        if any(text.startswith(p) for p in _DROP_PREFIXES):
            continue
        if text.startswith("Pressemitteilung des "):
            continue  # trailing related-link line, not body text
        nxt = _strip_tags(raw_paras[i + 1]) if i + 1 < len(raw_paras) else ""
        if nxt.startswith("Foto:"):
            continue  # image caption; the credit line is dropped above
        kept.append(raw)

    de_parts: list[str] = []
    en_parts: list[str] = []
    for raw in kept:
        for seg in _BR_RUN_RE.split(raw):
            seg_text = _strip_tags(_BR_RE.sub(" ", seg))
            if not seg_text:
                continue
            if _is_english_segment(seg, seg_text):
                en_parts.append(seg_text)
            else:
                de_parts.append(seg_text)

    body = "\n\n".join(de_parts).strip()
    body_en = "\n\n".join(en_parts).strip()
    if not body and not body_en:
        raise ValueError(
            "no document text found on this page (the reading-area "
            "body is empty after filtering) — the page may be a "
            "video/landing page"
        )
    return {
        "title": title,
        "published": published,
        "kind": kind_of_url(url, html_text),
        "body": body,
        "body_en": body_en,
        "has_english_translation": bool(body_en),
        "word_count": len(body.split()),
        "word_count_en": len(body_en.split()),
    }
