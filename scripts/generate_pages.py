#!/usr/bin/env python3
"""Generate page content (body HTML + metadata + summary) for every page in
config/keyword_map.json using Claude. Writes JSON to content/<slug>.json and
rendered HTML to site/<slug>/index.html using templates/page.html.template.

Run from the project root:
    python3 scripts/generate_pages.py [--only <slug>] [--force]

Requires ANTHROPIC_API_KEY in env (or in ../../.env / project root .env).
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, sys, html

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("pip install anthropic")

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
COMP = (ROOT / "config" / "competitor_analysis.md").read_text()
TEMPLATE = (ROOT / "templates" / "page.html.template").read_text()
CONTENT_DIR = ROOT / "content"
CONTENT_DIR.mkdir(exist_ok=True)
SITE_DIR = ROOT / "site"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

SITE = CONFIG["site"]

# ---------- env loading ----------
def load_env():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for p in [ROOT.parent.parent / ".env", ROOT.parent / ".env", pathlib.Path.home() / ".aiangels.env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return

load_env()
client = Anthropic()

# ---------- prompt ----------
SYSTEM = f"""You are an SEO copywriter producing pages for {SITE['name']}, an independent affiliate guide to boat rentals in Marbella, Spain.

WRITING STYLE
- Answer-first: every H2 section opens with a direct factual answer in 1–2 sentences, then expands.
- Specific numbers: real EUR prices, boat lengths in metres, group sizes, distances in nautical miles, durations in hours. Use the price anchors and ports listed below.
- British English. Energetic but not salesy. Honest about trade-offs (e.g. north wind days, choppy afternoons in August).
- No "in conclusion", no AI throat-clearing, no "in today's world", no "look no further".
- Local colour: name actual places (Puerto Banús, La Bajadilla, Cabopino, Estepona, Sotogrande, Funny Beach, Nikki Beach, Ocean Club, La Concha mountain, Gibraltar Rock).

SITE FACTS (use these consistently)
- Brand: {SITE['name']} — {SITE['tagline']}
- Domain: {SITE['domain']}
- WhatsApp / Phone: {SITE['phone_display']}
- Departure ports: {', '.join(SITE['departure_ports'])}
- Price anchors: 2 h low season €{SITE['price_anchor_low_2h']}, 2 h high season €{SITE['price_anchor_high_2h']}, full day 8 h €{SITE['price_anchor_fullday_8h']}.
- Inclusions in skippered charters: skipper, fuel, drinks, snacks.
- License-free rules (Spain): up to 5 m hull / 15 hp engine, 2 NM from coast, daylight, captain 18+.
- Affiliate fallback link (Click&Boat) is rendered separately in the page sidebar — do NOT embed it in the body.

COMPETITOR CONTEXT (for differentiation, do not copy):
{COMP[:1800]}

OUTPUT FORMAT (strict JSON, no prose, no code fences):
{{
  "meta_description": "<150–160 chars, includes primary keyword + 1 number + a CTA verb>",
  "summary": "<2 sentence factual summary of the page for internal-link-graph use>",
  "key_facts": ["<5–8 short bulleted facts, each ≤120 chars>"],
  "faq": [{{"q":"...","a":"..."}}, ... 5–8 Q&A pairs, answers 30–80 words each],
  "body_html": "<full <section>/<h2>/<p>/<ul>/<table>/<details> markup, ~{{TARGET_WORDS}} words, starts with an intro <p>, then 5–9 H2 sections, then a 'Frequently asked questions' H2 with <details><summary>question</summary><p>answer</p></details> blocks mirroring the faq array; never include <h1> (rendered separately), never include <html>/<head>/<body>, no inline CSS, no script>"
}}

Use a clear hub-and-spoke linking instinct: where natural, write phrases like "see our [yacht charter Marbella guide]" using markdown [anchor](/slug/) — these get post-processed. Use 3–6 such inline links to other site pages in the body. Available slugs:
- / (hub)
- /yacht-charter-marbella/
- /catamaran-rental-marbella/
- /fishing-boat-rental-marbella/
- /boat-rental-puerto-banus/
- /sunset-cruise-marbella/
- /boat-party-marbella/
- /boat-rental-no-license-marbella/
- /luxury-yacht-rental-marbella/
- /blog/how-much-does-it-cost-to-rent-a-boat-in-marbella/
- /blog/best-month-to-rent-a-boat-in-marbella/
- /blog/boat-license-rules-spain/
- /blog/puerto-banus-vs-marbella-marina/
- /blog/kids-on-a-boat-marbella/
- /blog/dolphin-watching-marbella/
- /blog/gibraltar-day-trip-by-boat/
- /blog/what-to-bring-on-a-boat-charter/
- /blog/seasickness-prevention-charter/
- /blog/private-vs-shared-boat-charter/

Always include at least one inline link to / (the hub).
"""

def build_user_prompt(page: dict, kind: str) -> str:
    return f"""Write the page for:

TITLE: {page['title']}
PRIMARY KEYWORD: {page['primary_keyword']}
SLUG: /{page['slug']}/ (kind: {kind})
H1: {page.get('h1', page['title'])}
INTENT: {page.get('intent','transactional')}
TARGET WORD COUNT: {page['target_words']}

Return only the JSON object specified in the system message."""

# ---------- markdown link → <a> ----------
MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
def md_links_to_html(s: str) -> str:
    return MD_LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)

# ---------- JSON-LD ----------
def jsonld_for(page: dict, kind: str, data: dict) -> str:
    url = f"{SITE['base_url']}/{page['slug']}/".replace("//", "/").replace(":/", "://")
    blocks = []
    blocks.append({
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "@id": SITE['base_url'] + "/#org",
        "name": SITE['name'],
        "url": SITE['base_url'] + "/",
        "telephone": SITE['phone_e164'],
        "email": SITE['email'],
        "areaServed": SITE['departure_ports'],
        "priceRange": f"€{SITE['price_anchor_low_2h']}–€{SITE['price_anchor_fullday_8h']}",
        "address": {"@type":"PostalAddress","addressLocality":"Marbella","addressRegion":"Andalucía","addressCountry":"ES"}
    })
    if kind == "blog":
        blocks.append({
            "@context":"https://schema.org","@type":"BlogPosting",
            "headline": page['title'], "url": url,
            "inLanguage":"en","author":{"@type":"Organization","name":SITE['name']},
            "publisher":{"@id":SITE['base_url']+"/#org"}
        })
    else:
        blocks.append({
            "@context":"https://schema.org","@type":"Service",
            "name": page['title'], "url": url,
            "provider":{"@id":SITE['base_url']+"/#org"},
            "areaServed":"Marbella, Spain",
            "offers":{"@type":"AggregateOffer","priceCurrency":"EUR","lowPrice":SITE['price_anchor_low_2h'],"highPrice":SITE['price_anchor_fullday_8h']}
        })
    if data.get("faq"):
        blocks.append({
            "@context":"https://schema.org","@type":"FAQPage",
            "mainEntity":[{"@type":"Question","name":f["q"],
                           "acceptedAnswer":{"@type":"Answer","text":f["a"]}} for f in data["faq"]]
        })
    crumbs = [{"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"}]
    if page['slug'].startswith("blog/"):
        crumbs.append({"@type":"ListItem","position":2,"name":"Guide","item":SITE['base_url']+"/blog/"})
        crumbs.append({"@type":"ListItem","position":3,"name":page['title'],"item":url})
    elif page['slug']:
        crumbs.append({"@type":"ListItem","position":2,"name":page['title'],"item":url})
    blocks.append({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":crumbs})
    return json.dumps(blocks, ensure_ascii=False)

def breadcrumb_html(page: dict) -> str:
    if not page['slug']:
        return ""
    parts = ['<nav class="breadcrumbs"><a href="/">Home</a> ›']
    if page['slug'].startswith("blog/"):
        parts.append(' <a href="/blog/">Guide</a> ›')
    parts.append(f' <span>{html.escape(page["title"])}</span></nav>')
    return "".join(parts)

# ---------- Claude call ----------
def generate(page: dict, kind: str) -> dict:
    prompt = build_user_prompt(page, kind)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=[{"type":"text","text":SYSTEM,"cache_control":{"type":"ephemeral"}}],
        messages=[{"role":"user","content":prompt}],
    )
    raw = msg.content[0].text.strip()
    # tolerate accidental code fences
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # try to recover up to last '}' then close arrays/objects
        last = raw.rfind("}")
        data = json.loads(raw[:last+1])
    return data

# ---------- render ----------
def render(page: dict, kind: str, data: dict) -> str:
    body = md_links_to_html(data["body_html"])
    # ensure H1 prepended
    h1 = page.get("h1", page['title'])
    body = f"<h1>{html.escape(h1)}</h1>\n" + body
    url = f"{SITE['base_url']}/{page['slug']}/".replace("//", "/").replace(":/", "://")
    if not page['slug']:
        url = SITE['base_url'] + "/"
    # depth-aware CSS href
    depth = page['slug'].count("/") + (1 if page['slug'] else 0)
    css_href = "../" * depth + "styles.css" if depth else "/styles.css"
    # Hero image: page may declare hero_img + hero_alt in data; else picsum seeded by slug
    seed = (page['slug'] or 'boat-rental-marbella').replace('/', '-')
    hero_img = data.get('hero_img') or f"https://picsum.photos/seed/{seed}/1600/700"
    hero_alt = data.get('hero_alt') or f"{page['primary_keyword']} — placeholder image"
    repl = {
        "{{HERO_IMG}}": hero_img,
        "{{HERO_ALT}}": html.escape(hero_alt),
        "{{TITLE}}": html.escape(page['title']),
        "{{META_DESCRIPTION}}": html.escape(data.get("meta_description", page.get("meta_description",""))),
        "{{CANONICAL_URL}}": url,
        "{{OG_TYPE}}": "article" if kind == "blog" else "website",
        "{{CSS_HREF}}": "/styles.css",
        "{{JSONLD}}": jsonld_for(page, kind, data),
        "{{BREADCRUMBS}}": breadcrumb_html(page),
        "{{BODY_HTML}}": body,
        "{{WHATSAPP_E164_NOPLUS}}": SITE['whatsapp_e164'].lstrip("+"),
        "{{PHONE_E164}}": SITE['phone_e164'],
        "{{PHONE_DISPLAY}}": SITE['phone_display'],
        "{{EMAIL}}": SITE['email'],
        "{{AFFILIATE_LINK}}": SITE['affiliate_link'],
    }
    out = TEMPLATE
    for k, v in repl.items():
        out = out.replace(k, v)
    return out

def write_page(page: dict, kind: str, html_str: str, data: dict):
    out_dir = SITE_DIR / page['slug'] if page['slug'] else SITE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html_str)
    (CONTENT_DIR / (page['slug'].replace("/", "_") or "index" )).with_suffix(".json").write_text(
        json.dumps({"page": page, "kind": kind, "data": data}, ensure_ascii=False, indent=2))

def iter_pages():
    yield ("hub", CONFIG["hub"])
    for s in CONFIG["spokes"]:
        yield ("spoke", s)
    for b in CONFIG["blog"]:
        yield ("blog", b)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="slug substring filter")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--render-only", action="store_true", help="render only pages with existing content cache; never call API")
    args = ap.parse_args()
    for kind, page in iter_pages():
        if args.only and args.only not in (page['slug'] or "index"):
            continue
        slug_id = page['slug'].replace("/", "_") or "index"
        cache_file = CONTENT_DIR / f"{slug_id}.json"
        if cache_file.exists() and not args.force:
            print(f"[render] {page['slug'] or '(hub)'} — from cache")
            data = json.loads(cache_file.read_text())["data"]
        else:
            if args.render_only:
                print(f"[skip] {page['slug'] or '(hub)'} — no cache, --render-only")
                continue
            print(f"[gen]  {page['slug'] or '(hub)'} ({kind}, {page['target_words']}w)")
            data = generate(page, kind)
        html_out = render(page, kind, data)
        write_page(page, kind, html_out, data)
    print("done.")

if __name__ == "__main__":
    main()
