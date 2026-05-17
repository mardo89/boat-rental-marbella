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
  <h2>On the water with us</h2>
  <div class="video-grid {single}">
{chr(10).join(cards)}
  </div>
</section>'''

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
        "logo": SITE['base_url'] + "/og-image.jpg",
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
        blocks.append({
            "@context":"https://schema.org","@type":"BlogPosting",
            "headline": page['title'], "url": url,
            "image": data.get('hero_img', SITE['base_url']+"/og-image.jpg"),
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
        byline = (f'<p class="byline">By <strong>{html.escape(SITE.get("editorial_team", SITE["name"]))}</strong>'
                  f' · Updated 16 May 2026 · Reviewed by local Marbella skippers</p>\n')
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
      <span class="boat-card-price">From <strong>€{low}</strong><small>2h skippered</small></span>
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

        BOAT_CARDS = [
            ("yacht-charter-marbella",  "Yacht Charter",       "Crewed motor yachts 10–22 m for cruising the Golden Mile.",        "12837089", 450, "4h", "Most popular"),
            ("catamaran-rental-marbella","Catamaran Rental",   "Stable twin-hull sail & power cats — best for families and groups.","32116621", 350, "4h", "Family favourite"),
            ("luxury-yacht-rental-marbella","Luxury Yachts",   "Crewed 18–30 m superyachts with chef, stewardess and water toys.", "30483267", 2400, "day", "Premium"),
            ("boat-rental-no-license-marbella","No-License Boats","Self-drive 5 m runabouts — no licence, no experience required.",  "144024",   130, "2h", "Self-drive"),
            ("fishing-boat-rental-marbella","Fishing Charters","Inshore & deep-sea charters — dorado, tuna, amberjack year-round.","36893149", 220, "2h", ""),
            ("boat-party-marbella","Boat Party",               "Group charters 10–40 guests — stag, hen, birthday, corporate.",    "27951598", 1200, "4h", ""),
        ]
        def _pex(id_, w):
            return f"https://images.pexels.com/photos/{id_}/pexels-photo-{id_}.jpeg?auto=compress&cs=tinysrgb&w={w}"
        cards_html = []
        for slug, title, desc, pid, price, dur, tag in BOAT_CARDS:
            tag_html = f'<span class="boat-card-tag">{html.escape(tag)}</span>' if tag else ''
            srcset = ", ".join(f"{_pex(pid, w)} {w}w" for w in (400, 600, 900))
            cards_html.append(f'''<a href="/{slug}/" class="boat-card">
  <div class="boat-card-img">
    <img src="{_pex(pid, 600)}" srcset="{srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(title)} in Marbella" loading="lazy" width="600" height="375">
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

    repl = {
        "{{HERO_EYEBROW}}": eyebrow_html,
        "{{HERO_H1}}": html.escape(h1),
        "{{HERO_SUB}}": html.escape(sub),
        "{{PRICE_LOW}}": str(SITE['price_anchor_low_2h']),
        "{{BOAT_GRID}}": BOAT_GRID,
        "{{HERO_IMG}}": hero_img,
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
