# bundesregierung-mcp 🇩🇪

mcp-name: io.github.mohammad-abbasi-sh/bundesregierung-mcp

Inoffizieller **Read-only**-MCP-Server für **[bundesregierung.de](https://www.bundesregierung.de)** — die offizielle Website der Bundesregierung — über ihre Listenseiten (Pressemitteilungen, Artikel / Meldungen, Reden & Pressekonferenzen) und Dokumentseiten, deren Volltext aus dem serverseitig gerenderten Lesebereich gelesen wird. Neueste Pressemitteilungen (612 beim letzten Check), Artikel (732) und Reden (567), neueste zuerst, Stichwortsuche über die gesamte Website und Volltext — manche Pressemitteilungen enthalten zusätzlich die offizielle englische Übersetzung inline. Kein Key, kein Login.

> Gebaut von Mohammad Abbasi im Rahmen der „Germany MCP factory" (Sepehr-Style-Pipeline). Nicht mit der Bundesregierung oder dem Presse- und Informationsamt der Bundesregierung verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m bundesregierung_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|--------------|
| `breg_press_releases` | Neueste Pressemitteilungen der Bundesregierung, neueste zuerst — `limit` 1..50, `page` ab 1. Einträge mit Titel, Topline, Link, Typ, Veröffentlichungszeit (Pressemitteilungen haben keine Teaser-Beschreibung) |
| `breg_articles` | Neueste Artikel / Meldungen, neueste zuerst — `limit` 1..50, `page` ab 1. Einträge mit Titel, Topline, Link, Veröffentlichungszeit und Kurzbeschreibung |
| `breg_speeches` | Neueste Reden, Pressestatements und Pressekonferenzen, neueste zuerst — meist vollständige Mitschriften („Im Wortlaut") — `limit` 1..50, `page` ab 1 |
| `breg_search` | Stichwortsuche über die gesamte Website (Pressemitteilungen, Artikel, Reden) — `query` (z. B. „Klima"), `limit` 1..50, `page` ab 1. Einträge verlinken über eine /breg-de/suche/-Alias-URL |
| `breg_get_document` | Volltext eines Dokuments — Pressemitteilung, Artikel oder Rede/Mitschrift — `url`: eine www.bundesregierung.de-Dokument-URL (/breg-de/aktuelles/... oder ein /breg-de/suche/-Alias). Liefert Titel, Veröffentlichungszeit, Art, den deutschen Text + Wortzahl und `body_en` mit der offiziellen englischen Übersetzung, wenn die Seite sie inline enthält |
| `breg_health` | Erreichbarkeits-Check (ok / blocked / error) — eine höfliche Anfrage |

Beispiel-Ausgabe (`breg_press_releases`, `limit` 1):

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

Hinweise:
- Der Server liest die **Listenseiten** der Website (`/breg-de/aktuelles/{pressemitteilungen,artikel,pressekonferenzen-und-reden}`, live geprüft am 2026-11-22). Die Ergebnisse sind serverseitig als `BPA.initialSearchResultsJson` im HTML eingebettet — es gibt **keinen RSS-Feed**: `/breg-de/service/rss-feeds` antwortet mit 404, und die Seiten enthalten keinen `<link rel="alternate">`-Feed.
- **Paginierungs-Eigenheit, live geprüft:** Das `?page=` der Website ist 0-basiert — `?page=N` liefert Seite N+1. Seite 1 enthält 11 Einträge, spätere Seiten 10. Die Listing-Tools laden weitere Seiten, bis das angefragte `limit` erreicht ist.
- **Dokumenttexte, ehrlich:** Der Volltext wird aus den serverseitig gerenderten `#rs_reading_area_content`-Absätzen gelesen (Statement: 7 deutsche + 8 englische Absätze inkl. Überschrift, 249 / 306 Wörter; Reden-Mitschrift: 20 Absätze, 1.113 Wörter; Artikel: 11 Absätze, 577 Wörter — alle live geprüft). Artikelseiten mischen Bildunterschrift + „Foto:"-Zeile und abschließende Verwandte-Links („Pressemitteilung des BMDS: ...") ein; alle drei werden aus dem Text herausgefiltert.
- **Englische Übersetzungen:** Manche Pressemitteilungen enthalten die offizielle englische Übersetzung inline (`lang="en-GB"`-Spans um ganze Absätze) — sie wird separat als `body_en` zurückgegeben (`has_english_translation: true`). Einzelne Fremdwörter (z. B. „EUDI-Wallet") sind ebenfalls mit `lang="en-GB"` markiert, aber nur wenige Zeichen lang; ein Abschnitt gilt erst als englisch, wenn die en-GB-Spans ≥ 50 % seines Texts abdecken.
- **Daten von Reden, ehrlich:** Reden-/Mitschrift-Seiten („Mitschrift Pressekonferenz") enthalten kein `<time datetime>` — ihr Datum wird aus der deutschen Datumszeile im Header gelesen („Freitag, 20. November 2026" → `2026-11-20`). Der Featured-Teaser (Bild-Teaser) der Artikel-Liste enthält ebenfalls kein `<time>` — sein Datum fällt auf das `sortDate`-Feld des Eintrags zurück (Ortszeit der Website, ohne Offset).
- Daten: öffentliche Listen- und Dokumentseiten von bundesregierung.de — kein Key, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst die drei echten mitgeschnittenen Listenseiten (Pressemitteilungen, Artikel, Website-Suche) plus drei echte Dokumentseiten (Pressemitteilung mit englischer Übersetzung, Artikel, Reden-Mitschrift)
- `tests/test_live.py` — vorsichtige Live-Anfragen an www.bundesregierung.de

Tests: 29/29 grün (22 offline + 7 live, 2026-11-22).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — kostenlos für persönliche und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
