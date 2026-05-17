#!/usr/bin/env python3
"""Generate the fleet pages: /boats/ (index) and /boats/<slug>/ (detail).

Reads config/boats.json. Renders through templates/page.html.template so the
header / hero / footer / book-card all match the rest of the site.
"""
from __future__ import annotations
import json, pathlib, html, re
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "page.html.template").read_text()
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
BOATS_CFG = json.loads((ROOT / "config" / "boats.json").read_text())
SITE = CONFIG["site"]
SITE_DIR = ROOT / "site"

_VID_PATH = ROOT / "config" / "videos.json"
VIDEOS_CFG = json.loads(_VID_PATH.read_text()) if _VID_PATH.exists() else {"videos": []}

def videos_for_url(url):
    # Accept either path ("/boats/azimut-39/") or absolute URL — normalize to path.
    path = url
    if path.startswith("http"):
        from urllib.parse import urlparse
        path = urlparse(path).path
    if not path.endswith("/"):
        path += "/"
    return [v for v in VIDEOS_CFG.get("videos", []) if path in v.get("placement", [])]

def video_section_html(videos):
    if not videos:
        return ""
    single = "single" if len(videos) == 1 else ""
    cards = []
    for v in videos:
        cards.append(f'''<figure class="video-card">
  <video controls preload="metadata" playsinline muted loop poster="/video/{v["slug"]}.jpg" width="720" height="1280">
    <source src="/video/{v["slug"]}.mp4" type="video/mp4">
  </video>
  <figcaption><strong>{html.escape(v["title"])}</strong>{html.escape(v["description"])}</figcaption>
</figure>''')
    return f'''<section class="video-section">
  <h2>On the water</h2>
  <div class="video-grid {single}">
{chr(10).join(cards)}
  </div>
</section>'''

_CUST_PATH = ROOT / "config" / "customers.json"
CUSTOMERS_CFG = json.loads(_CUST_PATH.read_text()) if _CUST_PATH.exists() else {"photos": []}

def guests_for_url(url):
    path = url
    if path.startswith("http"):
        from urllib.parse import urlparse
        path = urlparse(path).path
    if not path.endswith("/"):
        path += "/"
    return [p for p in CUSTOMERS_CFG.get("photos", []) if path in p.get("placement", [])]

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
    return [
        {
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
        } for v in videos
    ]

# ---------- helpers ----------
def pexels(id_, w=1600):
    return f"https://images.pexels.com/photos/{id_}/pexels-photo-{id_}.jpeg?auto=compress&cs=tinysrgb&w={w}"

def pexels_srcset(id_, widths):
    return ", ".join(f"{pexels(id_, w)} {w}w" for w in widths)

def boat_hero(boat, target_w=1600):
    """Return (src, srcset, alt) for the hero image — prefers local, falls back to Pexels."""
    if boat.get("hero_local"):
        src = boat["hero_local"]
        srcset_pairs = boat.get("hero_local_srcset") or [[src, target_w]]
        srcset = ", ".join(f"{p[0]} {p[1]}w" for p in srcset_pairs)
        alt = boat.get("hero_local_alt") or f"{boat['name']} — motor yacht charter Marbella"
        return src, srcset, alt
    pid = boat["hero_pexels_id"]
    return pexels(pid, target_w), pexels_srcset(pid, (640, 960, 1280, 1600)), f"{boat['name']} — motor yacht charter Marbella"

def boat_card_thumb(boat):
    """Return (src, srcset, alt) for the card thumbnail (smaller)."""
    if boat.get("hero_local"):
        srcset_pairs = boat.get("hero_local_srcset") or [[boat["hero_local"], 1600]]
        smaller = [p for p in srcset_pairs if p[1] <= 1200] or srcset_pairs
        src = smaller[-1][0]
        srcset = ", ".join(f"{p[0]} {p[1]}w" for p in srcset_pairs if p[1] <= 1200)
        alt = boat.get("hero_local_alt") or f"{boat['name']} — motor yacht charter Marbella"
        return src, srcset, alt
    pid = boat["hero_pexels_id"]
    return pexels(pid, 600), pexels_srcset(pid, (400, 600, 900)), f"{boat['name']} — motor yacht charter Marbella"

def wa_link(text):
    return f"https://wa.me/{SITE['whatsapp_e164'].lstrip('+')}?text=" + text.replace(" ", "%20").replace("'", "%27")

def boat_price_tier(boat):
    return BOATS_CFG["hourly_price_tiers"][boat["tier"]]

def lowest_price(boat):
    return min(boat_price_tier(boat)["prices"].values())

def entry_duration(boat):
    """Return the minimum-charter duration label, e.g. '2h' or '4h'."""
    tier = boat_price_tier(boat)
    mh = tier.get("min_hours")
    if mh:
        return f"{mh}h"
    # fall back to smallest key in prices grid
    keys = sorted(int(k.rstrip('h')) for k in tier["prices"].keys())
    return f"{keys[0]}h"

def all_inclusions(boat):
    """Return shared + boat-tier extra inclusions list."""
    extras = boat_price_tier(boat).get("extra_inclusions", [])
    return BOATS_CFG["shared_inclusions"] + extras

def jsonld_org():
    return {
        "@context":"https://schema.org","@type":["LocalBusiness","Organization"],
        "@id":SITE['base_url']+"/#org","name":SITE['name'],
        "url":SITE['base_url']+"/","logo":SITE['base_url']+"/og-image.jpg",
        "telephone":SITE['phone_e164'],"email":SITE['email'],
        "areaServed":SITE['departure_ports'],
        "sameAs":[u for u in [SITE.get('instagram_url'), SITE.get('facebook_url')] if u],
        "priceRange":f"€{SITE['price_anchor_low_2h']}–€{SITE['price_anchor_fullday_8h']}",
        "address":{"@type":"PostalAddress","addressLocality":"Marbella","addressRegion":"Andalucía","postalCode":"29602","addressCountry":"ES"},
        "geo":{"@type":"GeoCoordinates","latitude":SITE['geo_lat'],"longitude":SITE['geo_lng']},
        "foundingDate":str(SITE.get('founded_year',2025)),
    }

# ---------- /boats/ fleet index ----------
def render_index():
    boats = BOATS_CFG["boats"]

    cards = []
    for b in boats:
        src, srcset, alt = boat_card_thumb(b)
        low = lowest_price(b)
        cards.append(f'''<a href="/boats/{b["slug"]}/" class="boat-card">
  <div class="boat-card-img">
    <img src="{src}" srcset="{srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(alt)}" loading="lazy" width="600" height="375">
    <span class="boat-card-tag">{str(b["length_m"])}m · {b["capacity_pax"]} pax</span>
  </div>
  <div class="boat-card-body">
    <h3 class="boat-card-title">{html.escape(b["name"])}</h3>
    <p class="boat-card-desc">{html.escape(b["tagline"])}</p>
    <div class="boat-card-meta">
      <span class="boat-card-price">From <strong>€{low:,}</strong><small>{entry_duration(b)} skippered</small></span>
      <span class="boat-card-cta">View boat →</span>
    </div>
  </div>
</a>''')

    body = f'''<p class="byline">{len(boats)} boats in the fleet · Updated {date.today().strftime("%-d %B %Y")} · Skipper, fuel &amp; drinks included</p>

<p>Every charter from the fleet departs <a href="/boat-rental-puerto-banus/">Puerto Banús</a> with a licensed skipper, fuel, drinks, snorkel gear and water toys included — no surprise extras at the dock. Pick a boat below for full specs, photos and the hourly price grid, or message us on WhatsApp and we will match a boat to your group size and date.</p>

<section class="boat-grid-section" style="background:transparent;padding:24px 0 0">
  <div class="boat-grid" style="padding:0">
{chr(10).join(cards)}
  </div>
</section>

<h2>How the fleet works</h2>
<ul>
  <li><strong>Departure:</strong> all boats berth at Puerto Banús — see <a href="/boat-rental-puerto-banus/">Puerto Banús</a> for parking, pier map and arrival logistics.</li>
  <li><strong>Crew:</strong> licensed skipper for the full charter. No bareboat option on these boats.</li>
  <li><strong>Inclusions:</strong> {", ".join(BOATS_CFG["shared_inclusions"])}.</li>
  <li><strong>Extras:</strong> catered lunch (€25–€60 per head), DJ + speaker upgrade, beach club tender — request when you book.</li>
  <li><strong>Cancellation:</strong> full refund 7+ days out, weather cancellations always 100% refundable.</li>
</ul>

<p>Not sure which boat? <a href="/yacht-charter-marbella/">Read the yacht charter guide</a> or message us on WhatsApp — we will suggest the best fit for your group.</p>
'''

    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"CollectionPage",
            "name":"Marbella Boat Charter Fleet","url":SITE['base_url']+"/boats/",
            "description":"Our fleet of motor yachts available for charter from Puerto Banús, Marbella.",
            "isPartOf":{"@id":SITE['base_url']+"/#org"},
            "mainEntity":{
                "@type":"ItemList","numberOfItems":len(boats),
                "itemListElement":[
                    {"@type":"ListItem","position":i+1,
                     "url":SITE['base_url']+f"/boats/{b['slug']}/",
                     "name":b["name"]}
                    for i, b in enumerate(boats)
                ],
            },
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Boats","item":SITE['base_url']+"/boats/"},
            ],
        },
    ]

    hero_src, hero_srcset, _ = boat_hero(boats[0])
    jsonld += video_jsonld_blocks(videos_for_url("/boats/"), SITE['base_url']+"/boats/")
    write_page(
        slug="boats",
        title="Our Marbella Boat Charter Fleet — Yachts &amp; Catamarans",
        meta=f"Browse the {len(boats)}-boat charter fleet — Astondoa, Azimut and more. All from Puerto Banús with skipper, fuel and drinks included. From €749 / 2h.",
        h1="The Fleet",
        sub=f"Our Marbella boat charter fleet — every boat departs Puerto Banús with a licensed skipper, fuel, drinks and water toys included.",
        eyebrow="Boats · Marbella",
        hero_img=hero_src,
        hero_srcset=hero_srcset,
        hero_alt=f"Marbella charter fleet — motor yachts at Puerto Banús",
        body_html=body,
        jsonld=jsonld,
        breadcrumbs='<nav class="breadcrumbs"><a href="/">Home</a> › <span>Boats</span></nav>',
    )

# ---------- /boats/<slug>/ detail page ----------
def render_boat(boat):
    tier = boat_price_tier(boat)
    prices = tier["prices"]
    inclusions = all_inclusions(boat)
    tier_extras = tier.get("extra_inclusions", [])
    extended_note = tier.get("extended_note", "")
    hero_src, hero_srcset_str, hero_alt_text = boat_hero(boat)
    hero_id = boat.get("hero_pexels_id")  # still used for OG / JSON-LD fallback
    gallery = boat.get("gallery_pexels", [])
    name = boat["name"]

    # Price table
    price_rows = "\n".join(
        f"<tr><td>{dur}</td><td><strong>€{p:,}</strong></td></tr>"
        for dur, p in prices.items()
    )

    # Gallery thumbnails — prefer local
    gallery_html = ""
    gallery_local = boat.get("gallery_local") or []
    if gallery_local:
        thumbs = "".join(
            f'<figure class="inline-img"><img src="{g["src"]}" srcset="{", ".join(f"{p[0]} {p[1]}w" for p in g["srcset"])}" sizes="(max-width: 880px) 100vw, 720px" alt="{html.escape(g.get("alt", name))}" loading="lazy" width="1200" height="800"></figure>'
            for g in gallery_local
        )
        gallery_html = f'<h2>Gallery</h2>\n{thumbs}'
    elif gallery:
        thumbs = "".join(
            f'<figure class="inline-img"><img src="{pexels(gid, 1200)}" srcset="{pexels_srcset(gid, (480,768,1200))}" sizes="(max-width: 880px) 100vw, 720px" alt="{html.escape(name)} — Marbella" loading="lazy" width="1200" height="800"></figure>'
            for gid in gallery[1:]  # skip the hero (already rendered above the fold)
        )
        gallery_html = f'<h2>Gallery</h2>\n{thumbs}'

    # Highlights as list
    highlights_html = "<ul>" + "".join(f"<li>{html.escape(h)}</li>" for h in boat["highlights"]) + "</ul>"

    wa_text = f"Hi, I'd like to book the {name} in Marbella"
    other_boats = [b for b in BOATS_CFG["boats"] if b["slug"] != boat["slug"]]
    related_html = ""
    if other_boats:
        cards = []
        for b in other_boats:
            src, srcset, alt = boat_card_thumb(b)
            cards.append(f'''<a href="/boats/{b["slug"]}/" class="boat-card">
  <div class="boat-card-img">
    <img src="{src}" srcset="{srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(alt)}" loading="lazy" width="600" height="375">
    <span class="boat-card-tag">{str(b["length_m"])}m · {b["capacity_pax"]} pax</span>
  </div>
  <div class="boat-card-body">
    <h3 class="boat-card-title">{html.escape(b["name"])}</h3>
    <p class="boat-card-desc">{html.escape(b["tagline"])}</p>
    <div class="boat-card-meta">
      <span class="boat-card-price">From <strong>€{lowest_price(b)}</strong><small>2h skippered</small></span>
      <span class="boat-card-cta">View boat →</span>
    </div>
  </div>
</a>''')
        related_html = f'''<h2>Other boats in the fleet</h2>
<section class="boat-grid-section" style="background:transparent;padding:8px 0 0">
  <div class="boat-grid" style="padding:0">
{chr(10).join(cards)}
  </div>
</section>'''

    body = f'''<p class="byline"><strong>{boat["builder"]} {boat["length_m"]} m motor yacht</strong> · {boat["capacity_pax"]} guests · departs {html.escape(boat["departure_port"])}</p>

<p>{html.escape(boat["summary"])}</p>

<div class="callout">
  <strong>Quick specs:</strong> {boat["length_m"]} m · {boat["capacity_pax"]} pax · skipper included{(" · in fleet since " + str(boat["model_year"])) if boat.get("model_year") else ""} · departs {html.escape(boat["departure_port"])}.
  <br><strong>From €{lowest_price(boat):,} for {entry_duration(boat)}.</strong> Drinks, fuel, insurance &amp; VAT included.{(" Plus jet ski free for the day." if "Jet ski" in " ".join(tier_extras) else "")}
</div>

<h2>{("Pricing" if len(prices) == 1 else "Hourly pricing")}</h2>
<p>{("Minimum charter on the " + name + " is " + entry_duration(boat) + " — the rate below is all-in. Longer durations on request." if len(prices) == 1 else "Same boat, same crew — price scales with duration. Pick the length that fits your day:")}</p>
<table>
  <thead><tr><th>Duration</th><th>Price (EUR)</th></tr></thead>
  <tbody>
{price_rows}
  </tbody>
</table>
<p><em>All prices include: {", ".join(inclusions).lower()}. No hidden marina fees, no fuel surcharge for the standard coastal route.{(" " + extended_note) if extended_note else ""}</em></p>

<h2>What makes this boat work</h2>
{highlights_html}

<h2>What's included on every charter</h2>
<ul>
  <li><strong>Licensed skipper</strong> for the full duration</li>
  <li><strong>Drinks on board:</strong> water, soft drinks, beer, white wine and cava</li>
  <li><strong>Light snacks</strong> (fruit, crisps, almonds, biscuits)</li>
  <li><strong>Fuel</strong> for the standard Marbella–Estepona–Cabopino cruising loop</li>
  <li><strong>Insurance</strong> and full safety equipment (life jackets, flares, first aid)</li>
  <li><strong>Spanish IVA (VAT, 21%)</strong> — no surprise at checkout</li>
  <li><strong>Water toys:</strong> snorkel masks, inflatable donut, paddleboard</li>
  <li><strong>Towels</strong> for every guest</li>
  {chr(10).join(f'<li><strong>{html.escape(x)}</strong> — included on the {name}</li>' for x in tier_extras)}
</ul>
<p>Catered lunch, premium spirits, DJ and beach-club tender service can be added when you book.</p>

<h2>Where it departs from</h2>
<p>The {name} berths at <a href="/boat-rental-puerto-banus/">Puerto Banús</a> — the deepest charter marina on the Marbella coast and the most central pickup for guests staying on the Golden Mile. You will get the exact pier and slip number 24 hours before departure. Underground parking is 5 minutes from the pontoon.</p>

<h2>Typical day on the {name}</h2>
<ol>
  <li><strong>Boarding</strong> at Puerto Banús — welcome drinks, safety briefing.</li>
  <li><strong>Westbound run</strong> along the Golden Mile, past Marbella Club and Puente Romano.</li>
  <li><strong>Anchor stop</strong> at Cala del Faro or Río Verde for swim, snorkel and paddleboard.</li>
  <li><strong>Lunch on board</strong> (BYO or catered platter).</li>
  <li><strong>Optional</strong> tender to a beach club, or continue east towards Cabopino.</li>
  <li><strong>Return</strong> to Puerto Banús, sunset over La Concha mountain.</li>
</ol>

<h2>How to book</h2>
<p>WhatsApp us with your date and group size. We confirm availability within minutes, hold the boat for 24 hours with no deposit, and lock the booking once you confirm. Full refund up to 7 days out, weather cancellations always 100% refundable.</p>

{gallery_html}

{related_html}

<h2>Frequently asked questions</h2>
<details><summary>How many guests can the {name} carry?</summary><p>{boat["capacity_pax"]} guests for day charter. Overnight capacity is lower — typically 4–6 in cabins on a {boat["length_m"]} m yacht.</p></details>
<details><summary>Is the skipper included?</summary><p>Yes — every charter on the {name} comes with a licensed Spanish skipper. The captain handles navigation, anchoring and route planning. You and your group are guests for the day.</p></details>
<details><summary>What's included in the price?</summary><p>Skipper, fuel for the standard coastal route, drinks (water and soft drinks), Spanish IVA (VAT) and insurance. Catered lunch and alcohol are extras you can add when booking.</p></details>
<details><summary>Can we go further than the standard route?</summary><p>Yes — longer or further itineraries (Gibraltar day trip, Estepona-Sotogrande loop) are bookable. A fuel surcharge applies for itineraries beyond the standard 12–15 NM coastal cruise. We will quote it before you commit.</p></details>
<details><summary>What happens if the weather is bad?</summary><p>Skipper calls the night before. If forecast wind exceeds Force 4–5 or sea state makes the trip unsafe, you rebook or get a full refund. Light rain alone is not a cancellation reason on the Costa del Sol.</p></details>
'''

    # JSON-LD for boat detail: Product + AggregateOffer with per-duration offers
    offers = [
        {
            "@type":"Offer",
            "name":f"{name} – {dur} charter",
            "price": str(price),
            "priceCurrency":"EUR",
            "availability":"https://schema.org/InStock",
            "url": SITE['base_url']+f"/boats/{boat['slug']}/",
        }
        for dur, price in prices.items()
    ]
    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"Product",
            "name": f"{name} – Marbella Boat Charter",
            "description": boat["summary"],
            "brand":{"@type":"Brand","name":boat["builder"]},
            "category":"Boat Charter",
            "image": (SITE['base_url'] + hero_src) if hero_src.startswith('/') else hero_src,
            "url": SITE['base_url']+f"/boats/{boat['slug']}/",
            "offers":{
                "@type":"AggregateOffer",
                "priceCurrency":"EUR",
                "lowPrice": min(prices.values()),
                "highPrice": max(prices.values()),
                "offerCount": len(prices),
                "offers": offers,
            },
            "additionalProperty":[
                {"@type":"PropertyValue","name":"Length","value":f"{boat['length_m']} m"},
                {"@type":"PropertyValue","name":"Capacity","value":f"{boat['capacity_pax']} pax"},
                {"@type":"PropertyValue","name":"Departure","value":boat["departure_port"]},
                {"@type":"PropertyValue","name":"Type","value":boat["type"]},
            ] + ([{"@type":"PropertyValue","name":"In fleet since","value":str(boat["model_year"])}] if boat.get("model_year") else []),
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Boats","item":SITE['base_url']+"/boats/"},
                {"@type":"ListItem","position":3,"name":name,"item":SITE['base_url']+f"/boats/{boat['slug']}/"},
            ],
        },
    ]

    # Attach VideoObject schema for any videos placed on this boat URL
    boat_url = SITE['base_url']+f"/boats/{boat['slug']}/"
    jsonld += video_jsonld_blocks(videos_for_url(f"/boats/{boat['slug']}/"), boat_url)

    write_page(
        slug=f"boats/{boat['slug']}",
        title=f"{name} — {boat['builder']} {boat['length_m']}m Charter from Puerto Banús",
        meta=f"Charter the {name} from Puerto Banús — {boat['length_m']} m, {boat['capacity_pax']} guests, skipper & fuel included. From €{lowest_price(boat):,} for {entry_duration(boat)}.",
        h1=name,
        sub=html.unescape(boat["tagline"]),
        eyebrow=f"{boat['builder']} · {boat['length_m']}m · {boat['capacity_pax']} pax",
        hero_img=hero_src,
        hero_srcset=hero_srcset_str,
        hero_alt=hero_alt_text,
        body_html=body,
        jsonld=jsonld,
        breadcrumbs=f'<nav class="breadcrumbs"><a href="/">Home</a> › <a href="/boats/">Boats</a> › <span>{html.escape(name)}</span></nav>',
        wa_text=wa_text,
    )

# ---------- shared writer ----------
def write_page(slug, title, meta, h1, sub, eyebrow, hero_img, hero_srcset, hero_alt, body_html, jsonld, breadcrumbs, wa_text=None):
    url = f"{SITE['base_url']}/{slug}/"
    wa = wa_link(wa_text or "Hi, I'd like to book a boat in Marbella")
    repl = {
        "{{HERO_IMG}}": hero_img,
        "{{HERO_SRCSET}}": html.escape(hero_srcset),
        "{{HERO_ALT}}": html.escape(hero_alt),
        "{{HERO_EYEBROW}}": f'<span class="eyebrow">{html.escape(eyebrow)}</span>',
        "{{HERO_H1}}": html.escape(h1),
        "{{HERO_SUB}}": html.escape(sub),
        "{{TITLE}}": html.escape(title),
        "{{META_DESCRIPTION}}": html.escape(meta),
        "{{CANONICAL_URL}}": url,
        "{{OG_TYPE}}": "website",
        "{{CSS_HREF}}": "/styles.css",
        "{{JSONLD}}": json.dumps(jsonld, ensure_ascii=False),
        "{{PRICE_LOW}}": str(SITE['price_anchor_low_2h']),
        "{{BOAT_GRID}}": "",
        "{{BREADCRUMBS}}": breadcrumbs,
        "{{BODY_HTML}}": body_html,
        "{{VIDEO_SECTION}}": video_section_html(videos_for_url(url)),
        "{{GUESTS_SECTION}}": guests_section_html(guests_for_url(url)),
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
    # Override the WhatsApp deeplinks in the page-specific way for boat detail
    if wa_text:
        encoded = wa_text.replace(" ", "%20").replace("'", "%27")
        # Replace default booking message with boat-specific message on this page only
        out = out.replace(
            "Hi%2C%20I%27d%20like%20to%20book%20a%20boat%20in%20Marbella",
            encoded
        )
    out_path = SITE_DIR / slug / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)

def main():
    render_index()
    print(f"fleet index: site/boats/index.html")
    for b in BOATS_CFG["boats"]:
        render_boat(b)
        print(f"boat detail : site/boats/{b['slug']}/index.html")

if __name__ == "__main__":
    main()
