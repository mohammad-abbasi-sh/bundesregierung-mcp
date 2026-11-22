# bundesregierung-mcp 🇩🇪

mcp-name: io.github.mohammad-abbasi-sh/bundesregierung-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[bundesregierung.de](https://www.bundesregierung.de)** — وب‌سایت رسمی دولت فدرال آلمان — از طریق صفحه‌های فهرست (بیانیه‌های مطبوعاتی، مقاله‌ها / Meldungen، سخنرانی‌ها و کنفرانس‌های مطبوعاتی) و صفحه‌های اسناد، که متن کامل آن‌ها از بخش خواندنِ رندرشده در سمت سرور خوانده می‌شود. جدیدترین بیانیه‌های مطبوعاتی (۶۱۲ مورد در آخرین بررسی)، مقاله‌ها (۷۳۲) و سخنرانی‌ها (۵۶۷)، از جدید به قدیم، جست‌وجوی کلیدواژه در کل سایت، و متن کامل اسناد — برخی بیانیه‌ها ترجمهٔ رسمی انگلیسی را هم به‌صورت درون‌خطی دارند. بدون کلید، بدون ورود.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP آلمان» (خط لوله به سبک سپهر). وابسته به دولت فدرال آلمان یا دفتر مطبوعات و اطلاع‌رسانی دولت فدرال نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP اضافه کنید (stdio):

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

یا به‌صورت محلی اجرا کنید: `python -m bundesregierung_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `breg_press_releases` | جدیدترین بیانیه‌های مطبوعاتی (Pressemitteilungen) دولت فدرال آلمان، از جدید به قدیم — `limit` از ۱ تا ۵۰، `page` از ۱. هر مورد: عنوان، خط بالایی، لینک، نوع، زمان انتشار (تیزر بیانیه‌ها توضیح ندارد) |
| `breg_articles` | جدیدترین مقاله‌ها / Meldungen، از جدید به قدیم — `limit` از ۱ تا ۵۰، `page` از ۱. هر مورد: عنوان، خط بالایی، لینک، زمان انتشار و توضیح کوتاه |
| `breg_speeches` | جدیدترین سخنرانی‌ها، بیانیه‌های مطبوعاتی و کنفرانس‌های مطبوعاتی (Pressekonferenzen und Reden)، از جدید به قدیم — بیشتر رونوشت کامل («Im Wortlaut») — `limit` از ۱ تا ۵۰، `page` از ۱ |
| `breg_search` | جست‌وجوی کلیدواژه در کل سایت (بیانیه‌ها، مقاله‌ها، سخنرانی‌ها) — `query` (مثلاً «Klima»)، `limit` از ۱ تا ۵۰، `page` از ۱. لینک‌ها از طریق آدرس مستعار /breg-de/suche/ هستند |
| `breg_get_document` | متن کامل یک سند — بیانیه، مقاله یا سخنرانی/رونوشت — `url`: آدرس سند در www.bundesregierung.de (‎/breg-de/aktuelles/...‎ یا مستعار /breg-de/suche/). برمی‌گرداند: عنوان، زمان انتشار، نوع، متن آلمانی + تعداد کلمات، و `body_en` با ترجمهٔ رسمی انگلیسی وقتی سایت آن را درون‌خطی دارد |
| `breg_health` | بررسی دسترس‌پذیری (ok / blocked / error) — یک درخواست مؤدبانه |

نمونهٔ خروجی (`breg_press_releases` با `limit` برابر ۱):

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

نکته‌ها:
- سرور **صفحه‌های فهرست** سایت را می‌خواند (`/breg-de/aktuelles/{pressemitteilungen,artikel,pressekonferenzen-und-reden}`، بررسی زنده در ۲۰۲۶-۱۱-۲۲). نتیجه‌ها به‌صورت `BPA.initialSearchResultsJson` در سمت سرور داخل HTML جاسازی شده‌اند — **فید RSS وجود ندارد**: ‎/breg-de/service/rss-feeds‎ خطای ۴۰۴ می‌دهد و صفحه‌ها هیچ `<link rel="alternate">`ای ندارند.
- **ویژگی صفحه‌بندی، بررسی‌شده به‌صورت زنده:** پارامتر `?page=` سایت صفرمبناست — `?page=N` صفحهٔ N+1 را برمی‌گرداند. صفحهٔ ۱ یازده مورد و صفحه‌های بعد ده مورد دارند. ابزارهای فهرست تا رسیدن به `limit` درخواستی، صفحه‌های بعدی را هم می‌خوانند.
- **متن اسناد، صادقانه:** متن کامل از پاراگراف‌های `#rs_reading_area_content` که در سمت سرور رندر شده‌اند خوانده می‌شود (بیانیه: ۷ پاراگراف آلمانی + ۸ پاراگراف انگلیسی با احتساب تیتر، ۲۴۹ / ۳۰۶ کلمه؛ رونوشت سخنرانی: ۲۰ پاراگراف، ۱۱۱۳ کلمه؛ مقاله: ۱۱ پاراگراف، ۵۷۷ کلمه — همه نمونه‌های زنده). صفحه‌های مقاله زیرنویس عکس + خط «Foto:» و خط‌های پیوند مرتبط پایانی («Pressemitteilung des BMDS: ...») را هم دارند؛ هر سه از متن حذف می‌شوند.
- **ترجمه‌های انگلیسی:** برخی بیانیه‌ها ترجمهٔ رسمی انگلیسی را به‌صورت درون‌خطی دارند (اسپن‌های `lang="en-GB"` دور پاراگراف‌های کامل) — جداگانه به‌عنوان `body_en` برگردانده می‌شود (`has_english_translation: true`). واژه‌های خارجی تکی (مثلاً «EUDI-Wallet») هم با `lang="en-GB"` علامت خورده‌اند اما فقط چند حرف‌اند؛ یک بخش فقط وقتی انگلیسی شمرده می‌شود که اسپن‌های en-GB دست‌کم ۵۰٪ متن آن را بپوشانند.
- **تاریخ سخنرانی‌ها، صادقانه:** صفحه‌های سخنرانی/رونوشت («Mitschrift Pressekonferenz») هیچ `<time datetime>`ای ندارند — تاریخ آن‌ها از خط تاریخ آلمانی در سربرگ خوانده می‌شود («Freitag, 20. November 2026» → `2026-11-20`). تیزر شاخص (تصویری) فهرست مقاله‌ها هم `<time>` ندارد — تاریخ آن از فیلد `sortDate` مورد برداشته می‌شود (زمان محلی سایت، بدون آفست).
- داده‌ها: صفحه‌های فهرست و اسناد عمومی bundesregierung.de — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین، سه صفحهٔ فهرست واقعی ضبط‌شده (بیانیه‌ها، مقاله‌ها، جست‌وجوی سایت) به‌علاوهٔ سه صفحهٔ سند واقعی (بیانیه با ترجمهٔ انگلیسی، مقاله، رونوشت سخنرانی) را تجزیه می‌کند
- `tests/test_live.py` — درخواست‌های زندهٔ محتاطانه به www.bundesregierung.de

تست‌ها: ۲۹ از ۲۹ سبز (۲۲ آفلاین + ۷ زنده، ۲۰۲۶-۱۱-۲۲).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفادهٔ شخصی و غیرتجاری؛ استفادهٔ تجاری نیازمند مجوز جداگانه است (به LICENSE مراجعه کنید).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
