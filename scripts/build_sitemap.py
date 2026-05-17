#!/usr/bin/env python3
"""Generate sitemap.xml from keyword_map.json."""
import json, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
SITE = CONFIG["site"]
TODAY = datetime.date.today().isoformat()

def url(slug, prio, freq):
    loc = f"{SITE['base_url']}/{slug + '/' if slug else ''}"
    return f"  <url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><changefreq>{freq}</changefreq><priority>{prio}</priority></url>"

lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
         url("", "1.0", "weekly")]
for s in CONFIG["spokes"]:
    lines.append(url(s["slug"], "0.9", "weekly"))
lines.append(url("boats", "0.95", "weekly"))  # fleet index (high-intent)
import json as _json
boats_cfg = _json.loads((pathlib.Path(__file__).resolve().parents[1] / "config" / "boats.json").read_text())
for b in boats_cfg["boats"]:
    lines.append(url(f"boats/{b['slug']}", "0.9", "weekly"))
lines.append(url("blog", "0.8", "weekly"))  # blog index
for b in CONFIG["blog"]:
    lines.append(url(b["slug"], "0.7", "monthly"))
# Spanish (ES) priority pages
for es_slug, prio in [("es", "0.95"), ("es/alquiler-de-yates-marbella", "0.9"),
                      ("es/alquiler-barcos-puerto-banus", "0.9"),
                      ("es/alquiler-barcos-sin-licencia-marbella", "0.9")]:
    lines.append(url(es_slug, prio, "weekly"))
lines.append('</urlset>')
(ROOT / "site" / "sitemap.xml").write_text("\n".join(lines) + "\n")
print(f"sitemap.xml written ({1 + len(CONFIG['spokes']) + len(CONFIG['blog'])} URLs)")
