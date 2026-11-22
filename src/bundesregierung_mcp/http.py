"""HTTP layer for bundesregierung_mcp — plain httpx GETs against
www.bundesregierung.de.

Endpoints, all public, no key, no login:
- listing pages: https://www.bundesregierung.de/breg-de/aktuelles/
  {pressemitteilungen|artikel|pressekonferenzen-und-reden}?page=N
  (the site's ?page= is 0-based: ?page=N returns page N+1; the
  results are embedded server-side as BPA.initialSearchResultsJson
  in the HTML — see domain.parse_listing)
- site search: https://www.bundesregierung.de/breg-de/suche/
  992800!search?query=...&page=N (same embedded JSON shape)
- document pages: https://www.bundesregierung.de/breg-de/
  aktuelles/... (press releases, articles, speeches) and the
  /breg-de/suche/<slug>-<id> aliases the search results link to
  (they redirect to the canonical document URL).

Only www.bundesregierung.de is ever fetched.
"""
from __future__ import annotations

import os
import ssl
import time
from urllib.parse import urlparse

import httpx

from . import domain as _dom

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 25.0
ALLOWED_HOSTS = ("www.bundesregierung.de",)
HEALTH_URL = _dom.listing_url("pressemitteilungen", 1)


class BregError(RuntimeError):
    pass


def _verify():
    """TLS trust store: the OS bundle when present, else httpx/certifi.

    The OS bundle matters behind MITM egress proxies (their CA is in the
    system store, not in certifi) and is the right default on Linux
    anyway; on systems without it we fall back to certifi.
    """
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        ssl.get_default_verify_paths().openssl_cafile,
    ):
        if path and os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return True


def _client(accept: str) -> httpx.Client:
    # NOTE: we read the proxy URL from the environment but never log it.
    # trust_env=False because httpx fails to parse bracketed IPv6 entries
    # (e.g. [::1]) that some environments put in no_proxy.
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": accept},
        timeout=TIMEOUT,
        proxy=proxy or None,
        trust_env=False,
        verify=_verify(),
        follow_redirects=True,
    )


def _check_host(url: str) -> None:
    host = (urlparse(url).netloc or "").lower()
    if host not in ALLOWED_HOSTS:
        raise BregError(
            f"only {', '.join(ALLOWED_HOSTS)} pages are fetched "
            f"(got {host or url!r})"
        )


def _get(url: str, accept: str) -> tuple[str, str]:
    """GET with one retry on 429/5xx and on transient network errors.

    Returns (body text, final URL after redirects)."""
    _check_host(url)
    last_exc: Exception | None = None
    r: httpx.Response | None = None
    for attempt in range(2):
        try:
            with _client(accept) as c:
                r = c.get(url)
        except httpx.HTTPError as e:
            last_exc = e
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise BregError(f"network error fetching {url}: {e}") from e
        if r.status_code in (429, 500, 502, 503):
            if attempt == 0:
                time.sleep(1.0)
                continue
        break
    assert r is not None  # loop always assigns r or raises
    if r.status_code == 403:
        raise BregError(
            f"www.bundesregierung.de returned HTTP 403 for {url} (bot wall) — try again later"
        )
    if r.status_code == 429:
        raise BregError(
            "www.bundesregierung.de rate-limited the request (HTTP 429) — try again later"
        )
    if r.status_code != 200:
        raise BregError(
            f"www.bundesregierung.de returned HTTP {r.status_code} for {url}"
        )
    return r.text, str(r.url)


def fetch_listing(section: str, page: int) -> tuple[str, str]:
    """GET one listing page (1-based ``page``); returns
    (raw HTML, final URL)."""
    _dom.validate_section(section)
    _dom.validate_page(page)
    return _get(
        _dom.listing_url(section, page),
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    )


def fetch_search(query: str, page: int) -> tuple[str, str]:
    """GET one site-search page (1-based ``page``); returns
    (raw HTML, final URL)."""
    if not (query or "").strip():
        raise BregError("query must not be empty")
    _dom.validate_page(page)
    return _get(
        _dom.search_url(query.strip(), page),
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    )


def fetch_document(url: str) -> tuple[str, str]:
    """GET one www.bundesregierung.de document page; returns
    (raw HTML, final URL after redirects).

    Document URLs are /breg-de/aktuelles/... pages (press releases,
    articles, speeches) and /breg-de/suche/<slug>-<id> aliases.
    URLs with a fragment are refused, as are paths outside
    /breg-de/aktuelles/ and /breg-de/suche/.
    """
    parsed = urlparse(url)
    if parsed.fragment:
        raise BregError(
            "URLs with a fragment are not documents "
            f"(got {url!r})"
        )
    path = parsed.path
    if not (
        path.startswith("/breg-de/aktuelles/")
        or path.startswith("/breg-de/suche/")
    ):
        raise BregError(
            "only www.bundesregierung.de document URLs "
            "(/breg-de/aktuelles/... or /breg-de/suche/...) are "
            f"fetched (got {url!r})"
        )
    return _get(url, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")


def health_check() -> dict:
    """One polite probe of the press-releases listing.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `breg_health` tool
    and the daily smoke CI.
    """
    url = HEALTH_URL
    try:
        fetch_listing("pressemitteilungen", 1)
    except BregError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
