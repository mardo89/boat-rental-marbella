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

# ---------- video catalogue ----------
VIDEOS_CFG_PATH = ROOT / "config" / "videos.json"
VIDEOS_CFG = json.loads(VIDEOS_CFG_PATH.read_text()) if VIDEOS_CFG_PATH.exists() else {"videos": []}

def videos_for_slug(page_slug: str):
    """Return list of videos whose `placement` list contains the given page URL."""
    target = "/" + (page_slug + "/" if page_slug else "")
    target = target.replace("//", "/")
    out = []
    for v in VIDEOS_CFG.get("videos", []):
        if target in v.get("placement", []):
            out.append(v)
    return out

def video_section_html(videos):
    if not videos:
        return ""
    single = "single" if len(videos) == 1 else ""
    cards = []
    for v in videos:
        cards.append(f'''<figure class="video-card">
  <video controls preload="metadata" playsinline muted loop poster="/video/{v["slug"]}.jpg" width="720" height="1280">
    <source src="/video/{v["slug"]}.mp4" type="video/mp4">
    Your browser doesn't support HTML5 video.
  </video>
  <figcaption><strong>{html.escape(v["title"])}</strong>{html.escape(v["description"])}</figcaption>
</figure>''')
    return f'''<section class="video-section">
  <h2>Watch from on board</h2>
  <div class="video-grid {single}">
{chr(10).join(cards)}
  </div>
</section>'''

# ---------- fleet image catalogue ----------
# All landing-page imagery routes through this map. No Pexels anywhere visible.
def _fl(prefix, widths, alt):
    return {
        "src": f"{prefix}-{widths[-1]}.jpg",
        "srcset_hero": ", ".join(f"{prefix}-{w}.jpg {w}w" for w in widths),
        "srcset_inline": ", ".join(f"{prefix}-{w}.jpg {w}w" for w in widths if w <= 1200),
        "alt": alt,
        "widths": widths,
    }

FLEET_IMAGES = {
    "astondoa-hero":     _fl("/img/boats/astondoa-40/hero",       [600,900,1200,1600], "Astondoa 40 'Fufi' cruising in front of La Concha mountain, Marbella"),
    "astondoa-sunset":   _fl("/img/boats/astondoa-40/sunset",     [600,900,1200,1600], "Charter yacht arriving Puerto Banús marina at sunset"),
    "astondoa-interior": _fl("/img/boats/astondoa-40/interior",   [600,900,1200],      "Cream-leather saloon interior on our Marbella charter yacht"),
    "astondoa-lifestyle":_fl("/img/boats/astondoa-40/lifestyle",  [600,900,1200],      "Guests on the bow of a charter yacht in Puerto Banús, Marbella"),
    "azimut-hero":       _fl("/img/boats/azimut-39/hero",         [600,900,1200,1600], "Azimut 39 motor yacht cruising past La Concha mountain in Marbella"),
    "azimut-aerial":     _fl("/img/boats/azimut-39/aerial",       [600,900,1200],      "Azimut 39 from above — flybridge and cockpit detail"),
    "mangusta-hero":     _fl("/img/boats/mangusta-80/hero",       [600,900,1200,1600], "Mangusta 80 — biggest charter yacht in Marbella, past La Concha mountain"),
    "mangusta-aerial":   _fl("/img/boats/mangusta-80/aerial-wake",[600,900,1200],      "Mangusta 80 from above with wake — 24 m sport yacht on the Costa del Sol"),
    "mangusta-profile":  _fl("/img/boats/mangusta-80/profile",    [600,900,1200],      "Mangusta 80 profile view at anchor — Italian Overmarine sport yacht"),
    "mangusta-sun-pad":  _fl("/img/boats/mangusta-80/sun-pad",    [600,900,1200],      "Sun pad on the foredeck of the Mangusta 80 — group day charter"),
    "mangusta-saloon":   _fl("/img/boats/mangusta-80/saloon",     [600,900,1200],      "Mangusta 80 main saloon — refit luxury interior"),
    "mangusta-galley":   _fl("/img/boats/mangusta-80/galley",     [600,900,1200],      "Chef-grade galley on the Mangusta 80 — catered lunches on board"),
    "jetski-hero":       _fl("/img/jet-ski/hero",   [600,900,1200,1600], "Sea-Doo jet ski rental Marbella — two riders cruising past the Marbella mountains"),
    "jetski-cruise":     _fl("/img/jet-ski/cruise", [600,900,1200],      "Solo rider cruising on a Sea-Doo jet ski rental in Marbella"),
    "jetski-marina":     _fl("/img/jet-ski/marina", [600,900,1200],      "Jet ski rental at Puerto Banús marina, Marbella"),
    "jetski-fleet":      _fl("/img/jet-ski/fleet",  [600,900,1200],      "Sea-Doo jet ski fleet ready for rental in Marbella"),
    "dolphins-jumping":  _fl("/img/dolphins/dolphins-jumping", [600,900,1200,1600], "Dolphins jumping next to our boat off Marbella — first-party photo from a charter"),
    "fishing-big-catch": _fl("/img/fishing/big-catch-marbella", [600,900,1200,1600], "Big blue marlin landed on our Marbella fishing charter — two anglers, sport-fishing boat"),
    "fishing-family":    _fl("/img/fishing/family-fishing-marbella", [600,900,1200,1600], "Young angler trolling off Marbella on our sport-fishing charter"),
    "proposal-moment":   _fl("/img/proposal/proposal-moment", [600,900,1200,1600], "Proposal on a yacht in Marbella — bending knee with La Concha mountain behind"),
    "proposal-yes":      _fl("/img/proposal/proposal-yes", [600,900,1200,1600], "Saying yes during a Marbella yacht proposal cruise — La Concha mountain backdrop"),
    "proposal-embrace":  _fl("/img/proposal/proposal-embrace", [600,900,1200,1600], "Embrace after the proposal on a Marbella charter yacht"),
    "hen-group-pb":      _fl("/img/hen-party/hen-party-group-puerto-banus", [600,900,1200,1600], "Hen party group at Puerto Banús on our charter yacht — Marbella bachelorette weekend"),
    "hen-dolphins":      _fl("/img/hen-party/hen-party-dolphin-watching", [600,900,1200,1600], "Hen party watching dolphins from the bow on a Marbella charter yacht"),
    "hen-pink-balloons": _fl("/img/hen-party/hen-party-pink-balloons-bow", [600,900,1200,1600], "Pink balloon arch on the yacht bow at Puerto Banús — hen party decor"),
    "hen-balloon-letters":_fl("/img/hen-party/hen-party-balloon-letters", [600,900,1200,1600], "HEN balloon letters on a Marbella charter yacht stern"),
    "hen-soft-pink":     _fl("/img/hen-party/hen-party-soft-pink-arch", [600,900,1200,1600], "Soft pink balloon arch on the yacht bow at Puerto Banús — hen party charter"),
}

# Hero override per page slug (hub = empty string)
PAGE_HERO_MAP = {
    "": "mangusta-hero",
    "yacht-charter-marbella": "azimut-hero",
    "catamaran-rental-marbella": "mangusta-sun-pad",
    "fishing-boat-rental-marbella": "fishing-big-catch",
    "boat-rental-no-license-marbella": "astondoa-hero",
    "luxury-yacht-rental-marbella": "mangusta-hero",
    "sunset-cruise-marbella": "astondoa-sunset",
    "boat-party-marbella": "hen-group-pb",
    "boat-rental-puerto-banus": "astondoa-lifestyle",
    "jet-ski-rental-marbella": "jetski-hero",
    "blog/how-much-does-it-cost-to-rent-a-boat-in-marbella": "mangusta-aerial",
    "blog/best-month-to-rent-a-boat-in-marbella": "azimut-hero",
    "blog/boat-license-rules-spain": "azimut-hero",
    "blog/puerto-banus-vs-marbella-marina": "astondoa-sunset",
    "blog/kids-on-a-boat-marbella": "astondoa-hero",
    "blog/dolphin-watching-marbella": "dolphins-jumping",
    "blog/gibraltar-day-trip-by-boat": "mangusta-profile",
    "blog/what-to-bring-on-a-boat-charter": "astondoa-lifestyle",
    "blog/seasickness-prevention-charter": "azimut-hero",
    "blog/private-vs-shared-boat-charter": "mangusta-hero",
    "blog/astondoa-40-vs-smaller-yachts-marbella": "astondoa-interior",
    "blog/azimut-39-vs-smaller-yachts-marbella": "azimut-aerial",
    "blog/mangusta-80-vs-smaller-yachts-marbella": "mangusta-saloon",
}

# Per-page book-card override (price / duration label / pitch text)
PAGE_BOOK_CARD = {
    "jet-ski-rental-marbella": {
        "price": 200,
        "label": "1h Sea-Doo rental",
        "pitch": "Sea-Doo personal watercraft from Puerto Banús. Solo or two-up — same price. Briefing, life jacket and fuel included.",
    },
}

def book_card_for(slug):
    """Return (price, label, pitch) for the book-card on the given page slug."""
    ov = PAGE_BOOK_CARD.get(slug)
    if ov:
        return ov["price"], ov["label"], ov["pitch"]
    return (SITE['price_anchor_low_2h'],
            "2h skippered charter",
            "Instant quotes from local operators across Puerto Banús, Marbella Marina, Cabopino, Estepona &amp; Sotogrande.")

# Optional secondary inline image per page (for body figure)
PAGE_INLINE_MAP = {
    "": "astondoa-sunset",
    "yacht-charter-marbella": "mangusta-aerial",
    "catamaran-rental-marbella": "astondoa-hero",
    "fishing-boat-rental-marbella": "fishing-family",
    "boat-rental-no-license-marbella": "azimut-hero",
    "luxury-yacht-rental-marbella": "mangusta-profile",
    "sunset-cruise-marbella": "mangusta-hero",
    "boat-party-marbella": "hen-dolphins",
    "boat-rental-puerto-banus": "astondoa-sunset",
    "jet-ski-rental-marbella": "jetski-cruise",
    "blog/how-much-does-it-cost-to-rent-a-boat-in-marbella": "astondoa-sunset",
    "blog/best-month-to-rent-a-boat-in-marbella": "mangusta-hero",
    "blog/boat-license-rules-spain": "astondoa-hero",
    "blog/puerto-banus-vs-marbella-marina": "astondoa-lifestyle",
    "blog/kids-on-a-boat-marbella": "mangusta-sun-pad",
    "blog/dolphin-watching-marbella": "dolphins-jumping",
    "blog/gibraltar-day-trip-by-boat": "mangusta-aerial",
    "blog/what-to-bring-on-a-boat-charter": "astondoa-interior",
    "blog/seasickness-prevention-charter": "mangusta-aerial",
    "blog/private-vs-shared-boat-charter": "mangusta-aerial",
    "blog/astondoa-40-vs-smaller-yachts-marbella": "astondoa-hero",
    "blog/azimut-39-vs-smaller-yachts-marbella": "azimut-hero",
    "blog/mangusta-80-vs-smaller-yachts-marbella": "mangusta-hero",
}

def fleet_hero_for(slug):
    """Return (src, srcset, alt) for the page's hero, overriding any data hero."""
    key = PAGE_HERO_MAP.get(slug)
    if not key or key not in FLEET_IMAGES:
        return None
    img = FLEET_IMAGES[key]
    return (img["src"], img["srcset_hero"], img["alt"])

def fleet_inline_figure_html(slug):
    """Return a `<figure class='inline-img'>...</figure>` for the secondary body image."""
    key = PAGE_INLINE_MAP.get(slug)
    if not key or key not in FLEET_IMAGES:
        return ""
    img = FLEET_IMAGES[key]
    return (
        f'<figure class="inline-img"><img src="{img["src"]}" '
        f'srcset="{img["srcset_inline"]}" sizes="(max-width: 880px) 100vw, 720px" '
        f'alt="{html.escape(img["alt"])}" loading="lazy" width="1200" height="800">'
        f'</figure>'
    )

def replace_inline_pexels(body_html, slug):
    """Strip every `<figure class='inline-img'>` containing a Pexels URL.
    Inject one fleet inline figure at the first stripped position (if mapped)."""
    pattern = re.compile(r'\s*<figure class="inline-img">[\s\S]*?</figure>\s*')
    replacement = fleet_inline_figure_html(slug)
    matches = list(pattern.finditer(body_html))
    if not matches:
        return body_html
    # Keep ONE figure (replaced) at the position of the first match; strip the rest.
    pieces = []
    cursor = 0
    placed = False
    for m in matches:
        pieces.append(body_html[cursor:m.start()])
        if not placed and replacement:
            pieces.append("\n" + replacement + "\n")
            placed = True
        cursor = m.end()
    pieces.append(body_html[cursor:])
    return "".join(pieces)

CUSTOMERS_CFG_PATH = ROOT / "config" / "customers.json"
CUSTOMERS_CFG = json.loads(CUSTOMERS_CFG_PATH.read_text()) if CUSTOMERS_CFG_PATH.exists() else {"photos": []}

def guests_for_slug(page_slug: str):
    target = "/" + (page_slug + "/" if page_slug else "")
    target = target.replace("//", "/")
    return [p for p in CUSTOMERS_CFG.get("photos", []) if target in p.get("placement", [])]

def guests_section_html(photos):
    if not photos:
        return ""
    items = []
    for p in photos:
        sl = p["slug"]
        srcset = ", ".join(f"/img/customers/{sl}-{w}.jpg {w}w" for w in (400,600,900))
        items.append(
            f'<figure><img src="/img/customers/{sl}-600.jpg" srcset="{srcset}" '
            f'sizes="(max-width: 600px) 50vw, 240px" alt="{html.escape(p["alt"])}" '
            f'loading="lazy" width="600" height="800">'
            f'<figcaption>{html.escape(p["caption"])}</figcaption></figure>'
        )
    return (
        '<section class="guests-section">'
        f'<h2>{html.escape(CUSTOMERS_CFG.get("section_title","Guests on board"))}</h2>'
        f'<p class="guests-sub">{html.escape(CUSTOMERS_CFG.get("section_sub",""))}</p>'
        f'<div class="guests-grid">{"".join(items)}</div></section>'
    )

def guests_jsonld_blocks(photos, page_url):
    if not photos:
        return []
    return [{
        "@context": "https://schema.org",
        "@type": "ImageGallery",
        "name": f"Guests on board — {page_url}",
        "isPartOf": page_url,
        "image": [
            {
                "@type": "ImageObject",
                "contentUrl": SITE['base_url'] + f"/img/customers/{p['slug']}-900.jpg",
                "thumbnailUrl": SITE['base_url'] + f"/img/customers/{p['slug']}-400.jpg",
                "caption": p["caption"],
                "description": p["alt"],
            } for p in photos
        ],
    }]

def video_jsonld_blocks(videos, page_url):
    blocks = []
    for v in videos:
        blocks.append({
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": v["title"],
            "description": v["description"],
            "thumbnailUrl": SITE['base_url'] + f"/video/{v['slug']}.jpg",
            "contentUrl": SITE['base_url'] + f"/video/{v['slug']}.mp4",
            "uploadDate": "2026-05-17",
            "publisher": {"@id": SITE['base_url'] + "/#org"},
            "isPartOf": page_url,
            "keywords": ", ".join(v.get("tags", [])),
            "inLanguage": "en",
        })
    return blocks


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
    org_block = {
        "@context": "https://schema.org",
        "@type": ["LocalBusiness","Organization"],
        "@id": SITE['base_url'] + "/#org",
        "name": SITE['name'],
        "url": SITE['base_url'] + "/",
        "logo": SITE['base_url'] + "/img/logo-480.png",
        "telephone": SITE['phone_e164'],
        "email": SITE['email'],
        "areaServed": SITE['departure_ports'],
        "sameAs": [u for u in [SITE.get('instagram_url'), SITE.get('facebook_url')] if u],
        "priceRange": f"€{SITE['price_anchor_low_2h']}–€{SITE['price_anchor_fullday_8h']}",
        "address": {"@type":"PostalAddress","addressLocality":"Marbella","addressRegion":"Andalucía","postalCode":"29602","addressCountry":"ES"},
    }
    if SITE.get('geo_lat') and SITE.get('geo_lng'):
        org_block["geo"] = {"@type":"GeoCoordinates","latitude":SITE['geo_lat'],"longitude":SITE['geo_lng']}
    if SITE.get('founded_year'):
        org_block["foundingDate"] = str(SITE['founded_year'])
    blocks.append(org_block)
    if kind == "blog":
        # Prefer fleet hero (absolute URL) for BlogPosting.image; fall back to data
        fleet = fleet_hero_for(page['slug'])
        blog_image = SITE['base_url'] + fleet[0] if fleet else data.get('hero_img', SITE['base_url']+"/og-image.jpg")
        blocks.append({
            "@context":"https://schema.org","@type":"BlogPosting",
            "headline": page['title'], "url": url,
            "image": blog_image,
            "inLanguage":"en",
            "author":{"@type":"Organization","name":SITE.get('editorial_team', SITE['name']),"url":SITE['base_url']+"/"},
            "publisher":{"@id":SITE['base_url']+"/#org"},
            "datePublished":"2026-05-16","dateModified":"2026-05-16"
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
    # Page-attached videos → VideoObject
    blocks += video_jsonld_blocks(videos_for_slug(page['slug']), url)
    blocks += guests_jsonld_blocks(guests_for_slug(page['slug']), url)
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
    # Scrub any Pexels inline images, substitute one fleet image per page
    body = replace_inline_pexels(body, page['slug'])
    # add responsive srcset to inline pexels imgs that don't already have one
    def _add_srcset(m):
        tag = m.group(0)
        if 'srcset=' in tag: return tag
        src = re.search(r'src="([^"]+)"', tag).group(1)
        if 'pexels.com' not in src: return tag
        def _v(u, w):
            u2 = re.sub(r'[?&]w=\d+', '', u).rstrip('?&')
            sep = '&' if '?' in u2 else '?'
            return f"{u2}{sep}w={w}"
        srcset = ", ".join(f"{_v(src, w)} {w}w" for w in (480, 768, 1200))
        return tag.replace('<img ', f'<img srcset="{srcset}" sizes="(max-width: 880px) 100vw, 760px" ', 1)
    body = re.sub(r'<img [^>]+>', _add_srcset, body)
    # H1 is rendered in hero overlay (no duplicate); only byline + body here
    byline = ""
    if kind == "blog":
        byline = (
            '<div class="post-author">\n'
            '  <img class="post-author-avatar" src="/img/team/andra-kiirkivi-200.jpg" srcset="/img/team/andra-kiirkivi-200.jpg 200w, /img/team/andra-kiirkivi-400.jpg 400w" sizes="56px" width="56" height="56" alt="Andra Kiirkivi — Founder &amp; CEO, Boat Rental Marbella" loading="lazy">\n'
            '  <div class="post-author-meta">\n'
            '    <span class="post-author-name">By <strong>Andra Kiirkivi</strong></span>\n'
            '    <span class="post-author-role">Founder &amp; CEO · Boat Rental Marbella · Updated 20 May 2026 · Reviewed by local Marbella skippers</span>\n'
            '  </div>\n'
            '</div>\n'
        )
    body = byline + body
    url = f"{SITE['base_url']}/{page['slug']}/".replace("//", "/").replace(":/", "://")
    if not page['slug']:
        url = SITE['base_url'] + "/"
    # depth-aware CSS href
    depth = page['slug'].count("/") + (1 if page['slug'] else 0)
    css_href = "../" * depth + "styles.css" if depth else "/styles.css"
    # Hero image: page may declare hero_img + hero_alt in data; else picsum seeded by slug
    seed = (page['slug'] or 'boat-rental-marbella').replace('/', '-')
    hero_img = data.get('hero_img') or f"https://picsum.photos/seed/{seed}/1600/700"
    # keyword-bearing alt — falls back to data hero_alt + primary keyword for SEO weight
    hero_alt = f"{page['primary_keyword']} — {data.get('hero_alt','Marbella yacht')}"
    # build srcset for Pexels-hosted images by swapping the ?w param
    def _pexels_variant(u, w):
        return re.sub(r'[?&]w=\d+', '', u).rstrip('?&') + ('?' if '?' not in u else '&') + f'w={w}'
    hero_srcset = ", ".join(f"{_pexels_variant(hero_img, w)} {w}w" for w in (640, 960, 1280, 1600))
    # OVERRIDE with curated fleet image where mapped (no Pexels on landing pages)
    fleet = fleet_hero_for(page['slug'])
    if fleet:
        hero_img, hero_srcset, fleet_alt = fleet
        hero_alt = f"{page['primary_keyword']} — {fleet_alt}"

    # Hero overlay text — H1, subtitle (from meta), eyebrow
    h1 = page.get("h1", page['title'])
    meta_desc = data.get("meta_description", page.get("meta_description",""))
    # subtitle: first sentence or up to 160 chars
    sub = re.split(r'(?<=[.!?])\s+', meta_desc.strip(), maxsplit=1)[0]
    if len(sub) > 170: sub = sub[:165].rsplit(' ',1)[0] + '…'
    if kind == "hub":
        eyebrow_text = "Marbella · Costa del Sol"
    elif kind == "blog":
        eyebrow_text = "Guide · Marbella"
    else:
        eyebrow_text = "Marbella charter · 2026"
    eyebrow_html = f'<span class="eyebrow">{html.escape(eyebrow_text)}</span>'

    # Boat-type grid — render only on hub
    BOAT_GRID = ""
    if kind == "hub":
        # ---- Featured fleet section (from config/boats.json) ----
        def _pex(id_, w):
            return f"https://images.pexels.com/photos/{id_}/pexels-photo-{id_}.jpeg?auto=compress&cs=tinysrgb&w={w}"
        FLEET_SECTION = ""
        try:
            boats_cfg_path = pathlib.Path(__file__).resolve().parents[1] / "config" / "boats.json"
            boats_cfg = json.loads(boats_cfg_path.read_text())
            fleet_cards = []
            for b in boats_cfg["boats"]:
                tier = boats_cfg["hourly_price_tiers"][b["tier"]]
                low = min(tier["prices"].values())
                entry_dur = f"{tier.get('min_hours') or sorted(int(k.rstrip('h')) for k in tier['prices'].keys())[0]}h"
                # Prefer local image variants; fall back to Pexels
                if b.get("hero_local"):
                    srcset_pairs = b.get("hero_local_srcset") or [[b["hero_local"], 1600]]
                    small = [p for p in srcset_pairs if p[1] <= 1200] or srcset_pairs
                    card_src = small[-1][0]
                    card_srcset = ", ".join(f"{p[0]} {p[1]}w" for p in srcset_pairs if p[1] <= 1200)
                    card_alt = b.get("hero_local_alt") or f"{b['name']} — motor yacht charter Marbella"
                else:
                    pid = b["hero_pexels_id"]
                    card_src = _pex(pid, 600)
                    card_srcset = ", ".join(f"{_pex(pid, w)} {w}w" for w in (400, 600, 900))
                    card_alt = f"{b['name']} — motor yacht charter Marbella"
                fleet_cards.append(f'''<a href="/boats/{b["slug"]}/" class="boat-card">
  <div class="boat-card-img">
    <img src="{card_src}" srcset="{card_srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(card_alt)}" loading="lazy" width="600" height="375">
    <span class="boat-card-tag">{b["length_m"]}m · {b["capacity_pax"]} pax</span>
  </div>
  <div class="boat-card-body">
    <h3 class="boat-card-title">{html.escape(b["name"])}</h3>
    <p class="boat-card-desc">{html.escape(b["tagline"])}</p>
    <div class="boat-card-meta">
      <span class="boat-card-price">From <strong>€{low:,}</strong><small>{entry_dur} skippered</small></span>
      <span class="boat-card-cta">View boat →</span>
    </div>
  </div>
</a>''')
            if fleet_cards:
                FLEET_SECTION = f'''<section class="boat-grid-section" style="background:linear-gradient(180deg, var(--c-sand) 0%, #fff 100%)">
  <div class="section-head">
    <span class="eyebrow">Our fleet</span>
    <h2>Boats you can charter today</h2>
    <p>The actual yachts in our Puerto Banús fleet — pick a boat, message us on WhatsApp, book in 60 seconds.</p>
  </div>
  <div class="boat-grid">
    {"".join(fleet_cards)}
  </div>
  <div style="text-align:center;margin-top:28px">
    <a href="/boats/" class="btn-hero-ghost" style="background:var(--c-sea-l);color:var(--c-sea-d);border-color:#cfe5f4">See the full fleet →</a>
  </div>
</section>'''
        except Exception as e:
            print(f"[warn] fleet section skipped: {e}")

        # Each category card now uses a curated FLEET_IMAGE
        BOAT_CARDS = [
            ("yacht-charter-marbella",       "Yacht Charter",   "Crewed motor yachts cruising the Golden Mile — from €749/2h.",                   "azimut-hero",       749,  "2h",  "Most popular"),
            ("catamaran-rental-marbella",    "Catamaran Rental","Looking for a catamaran? Our flat-deck Mangusta 80 sun-pad delivers the same.", "mangusta-sun-pad",  749,  "2h",  "Group favourite"),
            ("luxury-yacht-rental-marbella", "Luxury Yachts",   "Mangusta 80 — biggest yacht charter in Marbella, jet ski included.",            "mangusta-hero",     4719, "4h",  "Flagship"),
            ("boat-rental-no-license-marbella","No-License Boats","Skip the licence — our skippered fleet handles everything.",                  "astondoa-hero",     749,  "2h",  "Skippered"),
            ("fishing-boat-rental-marbella", "Fishing Charters","Inshore fishing on our 12.5 m fleet — light tackle and trolling.",              "fishing-big-catch",749,  "2h",  ""),
            ("boat-party-marbella",          "Boat Party",      "Group charters up to 12 guests — stag, hen, birthday, corporate.",              "mangusta-aerial",   749,  "2h",  ""),
            ("jet-ski-rental-marbella",      "Jet Ski Rental",  "Sea-Doo PWC from Puerto Banús — solo or two-up. Free with Mangusta 80.",        "jetski-hero",       200,  "1h",  "Sea-Doo"),
        ]
        cards_html = []
        for slug, title, desc, fkey, price, dur, tag in BOAT_CARDS:
            tag_html = f'<span class="boat-card-tag">{html.escape(tag)}</span>' if tag else ''
            fimg = FLEET_IMAGES[fkey]
            srcset = ", ".join(f"{fimg['src'].replace('-' + str(fimg['widths'][-1]) + '.jpg', f'-{w}.jpg')} {w}w" for w in fimg['widths'] if w <= 900)
            cards_html.append(f'''<a href="/{slug}/" class="boat-card">
  <div class="boat-card-img">
    <img src="{fimg['src'].replace('-' + str(fimg['widths'][-1]) + '.jpg', '-600.jpg')}" srcset="{srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(title)} in Marbella — {html.escape(fimg['alt'])}" loading="lazy" width="600" height="375">
    {tag_html}
  </div>
  <div class="boat-card-body">
    <h3 class="boat-card-title">{html.escape(title)}</h3>
    <p class="boat-card-desc">{html.escape(desc)}</p>
    <div class="boat-card-meta">
      <span class="boat-card-price">From <strong>€{price}</strong><small>{dur} charter</small></span>
      <span class="boat-card-cta">Explore →</span>
    </div>
  </div>
</a>''')
        category_section = f'''<section class="boat-grid-section">
  <div class="section-head">
    <span class="eyebrow">Browse by boat type</span>
    <h2>Find the right boat for your day</h2>
    <p>Six categories covering every group size, budget and experience level on the Costa del Sol.</p>
  </div>
  <div class="boat-grid">
    {"".join(cards_html)}
  </div>
</section>'''
        BOAT_GRID = FLEET_SECTION + category_section

    # hreflang for EN ↔ ES mapping (only for pages that have an ES counterpart)
    EN_TO_ES = {
        "": "/es/",
        "yacht-charter-marbella": "/es/alquiler-de-yates-marbella/",
        "boat-rental-puerto-banus": "/es/alquiler-barcos-puerto-banus/",
        "boat-rental-no-license-marbella": "/es/alquiler-barcos-sin-licencia-marbella/",
    }
    es_alt = EN_TO_ES.get(page['slug'])
    es_target = es_alt or "/es/"  # fallback: ES hub
    hreflang_block = ""
    if es_alt:
        hreflang_block = (
            f'<link rel="alternate" hreflang="en" href="{url}">\n'
            f'<link rel="alternate" hreflang="es" href="{SITE["base_url"]}{es_alt}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{url}">'
        )
    lang_switcher = f'<strong>EN</strong><span class="sep">|</span><a href="{es_target}" hreflang="es" rel="alternate">ES</a>'
    lang_switcher_footer = f'<strong>🇬🇧 English</strong> &nbsp;·&nbsp; <a href="{es_target}" hreflang="es" rel="alternate">🇪🇸 Español</a>'
    repl = {
        "{{HREFLANG}}": hreflang_block,
        "{{LANG_SWITCHER}}": lang_switcher,
        "{{LANG_SWITCHER_FOOTER}}": lang_switcher_footer,
        "{{HERO_EYEBROW}}": eyebrow_html,
        "{{HERO_H1}}": html.escape(h1),
        "{{HERO_SUB}}": html.escape(sub),
        "{{PRICE_LOW}}": str(book_card_for(page['slug'])[0]),
        "{{PRICE_LABEL}}": book_card_for(page['slug'])[1],
        "{{BOOK_PITCH}}": book_card_for(page['slug'])[2],
        "{{BOAT_GRID}}": BOAT_GRID,
        "{{HERO_IMG}}": hero_img,
        "{{OG_IMG}}": (SITE['base_url'] + hero_img) if hero_img.startswith('/') else hero_img,
        "{{HERO_SRCSET}}": html.escape(hero_srcset),
        "{{HERO_ALT}}": html.escape(hero_alt),
        "{{TITLE}}": html.escape(page['title']),
        "{{META_DESCRIPTION}}": html.escape(data.get("meta_description", page.get("meta_description",""))),
        "{{CANONICAL_URL}}": url,
        "{{OG_TYPE}}": "article" if kind == "blog" else "website",
        "{{CSS_HREF}}": "/styles.css",
        "{{JSONLD}}": jsonld_for(page, kind, data),
        "{{BREADCRUMBS}}": breadcrumb_html(page),
        "{{BODY_HTML}}": body,
        "{{VIDEO_SECTION}}": video_section_html(videos_for_slug(page['slug'])),
        "{{GUESTS_SECTION}}": guests_section_html(guests_for_slug(page['slug'])),
        "{{WHATSAPP_E164_NOPLUS}}": SITE['whatsapp_e164'].lstrip("+"),
        "{{PHONE_E164}}": SITE['phone_e164'],
        "{{PHONE_DISPLAY}}": SITE['phone_display'],
        "{{EMAIL}}": SITE['email'],
        "{{AFFILIATE_LINK}}": SITE['affiliate_link'],
        "{{INSTAGRAM_URL}}": SITE.get('instagram_url',''),
        "{{INSTAGRAM_HANDLE}}": SITE.get('instagram_handle',''),
        "{{FACEBOOK_URL}}": SITE.get('facebook_url',''),
        "{{FACEBOOK_LABEL}}": SITE.get('facebook_label','Facebook'),
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
