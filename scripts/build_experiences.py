#!/usr/bin/env python3
"""Build the /experiences/ hub + per-experience landing pages.

Each experience either links out to an existing spoke (boat-party, sunset, fishing, jet-ski) or
to a dedicated /experiences/<slug>/ landing page. Run via deploy.sh.
"""
from __future__ import annotations
import json, pathlib, html
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "page.html.template").read_text()
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
SITE = CONFIG["site"]
SITE_DIR = ROOT / "site"

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

# Experience catalogue — each card on the hub. Order = display order on hub.
EXPERIENCES = [
    {"slug":"/boat-party-marbella/", "title":"Onboard Parties", "desc":"Stag, hen, birthday & group charters with BYO welcomed, DJ add-on, ice tubs.", "image":"/img/boats/mangusta-80/aerial-wake", "widths":(400,600,900), "tag":"Most popular", "from":749},
    {"slug":"/experiences/bachelor-hen-parties-marbella/", "title":"Bachelor & Hen Parties", "desc":"The full Marbella weekend script — yacht morning, beach-club tender, dinner ashore.", "image":"/img/customers/h02", "widths":(400,600,900), "tag":"Groups 9-12", "from":749},
    {"slug":"/sunset-cruise-marbella/", "title":"Romantic Sunset", "desc":"Two hours from Puerto Banús, under La Concha as the lights come on the Golden Mile.", "image":"/img/boats/astondoa-40/sunset", "widths":(600,900,1200), "tag":"Couples", "from":749},
    {"slug":"/experiences/family-boat-days-marbella/", "title":"Family Boat Days", "desc":"Calm-water itineraries, snorkel stops, snacks pre-loaded for under-12s.", "image":"/img/boats/astondoa-40/hero", "widths":(600,900,1200), "tag":"Kids friendly", "from":749},
    {"slug":"/fishing-boat-rental-marbella/", "title":"Fishing Trips", "desc":"Inshore reef fishing — light tackle, dorado in summer, amberjack year-round.", "image":"/img/boats/astondoa-40/lifestyle", "widths":(600,900,1200), "tag":"", "from":749},
    {"slug":"/experiences/photoshoot-yacht-marbella/", "title":"Photoshoot on a Yacht", "desc":"Influencer, fashion or wedding photos with the La Concha backdrop.", "image":"/img/boats/mangusta-80/sun-pad", "widths":(600,900,1200), "tag":"Content day", "from":749},
    {"slug":"/jet-ski-rental-marbella/", "title":"Jet Ski Experience", "desc":"Sea-Doo from Puerto Banús — solo or two-up, briefing included, no licence needed.", "image":"/img/jet-ski/hero", "widths":(600,900,1200), "tag":"Adrenaline", "from":200},
    {"slug":"/blog/dolphin-watching-marbella/", "title":"Dolphin Watching", "desc":"4-hour offshore charter — bottlenose, common & striped pods 2–8 NM out.", "image":"/img/boats/mangusta-80/aerial-wake", "widths":(600,900,1200), "tag":"Wildlife", "from":749},
    {"slug":"/blog/gibraltar-day-trip-by-boat/", "title":"Gibraltar Day Trip", "desc":"95 NM round trip from Puerto Banús past Sotogrande to the Rock and back.", "image":"/img/boats/mangusta-80/profile", "widths":(600,900,1200), "tag":"Adventure", "from":1500},
    # Tier-1 new
    {"slug":"/experiences/wedding-yacht-marbella/", "title":"Wedding on a Yacht", "desc":"Civil ceremony at anchor, reception on the flybridge, photos under La Concha.", "image":"/img/customers/h04", "widths":(400,600,900), "tag":"Once in a lifetime", "from":2299},
    {"slug":"/experiences/corporate-yacht-marbella/", "title":"Corporate & Team Building", "desc":"Client hosting, team days, incentive trips — invoiced with full Spanish IVA.", "image":"/img/boats/mangusta-80/saloon", "widths":(600,900,1200), "tag":"B2B", "from":1299},
    {"slug":"/experiences/honeymoon-yacht-marbella/", "title":"Honeymoon Charter", "desc":"Private cruise + romantic dinner at anchor + sunrise breakfast onboard.", "image":"/img/boats/astondoa-40/interior", "widths":(600,900,1200), "tag":"Newlyweds", "from":1299},
    {"slug":"/experiences/snorkeling-tour-marbella/", "title":"Snorkeling Tour", "desc":"Two anchor stops at the clearest spots between Cabopino and Cala del Faro.", "image":"/img/customers/h11", "widths":(400,600,900), "tag":"All ages", "from":749},
    {"slug":"/experiences/birthday-yacht-marbella/", "title":"Birthday on a Yacht", "desc":"Cava at noon, anchor swim, dinner ashore — birthday script for any age.", "image":"/img/customers/h14", "widths":(400,600,900), "tag":"Celebrate", "from":749},
    {"slug":"/experiences/proposal-yacht-marbella/", "title":"Proposal on a Yacht", "desc":"Skipper-coordinated proposal at sunset off Río Verde with cava and the rings hidden.", "image":"/img/customers/h04", "widths":(400,600,900), "tag":"She/he said yes", "from":749},
    {"slug":"/experiences/anniversary-yacht-marbella/", "title":"Anniversary Cruise", "desc":"A quiet half-day for two — sunset, an anchor stop, dinner at anchor or ashore.", "image":"/img/boats/astondoa-40/sunset", "widths":(600,900,1200), "tag":"Marking it", "from":749},
]

def card_html(exp):
    base = exp["image"]
    widths = exp["widths"]
    srcset = ", ".join(f"{base}-{w}.jpg {w}w" for w in widths)
    src = f"{base}-{widths[1]}.jpg"
    tag_html = f'<span class="boat-card-tag">{html.escape(exp["tag"])}</span>' if exp.get("tag") else ''
    return f'''<a href="{exp["slug"]}" class="boat-card">
  <div class="boat-card-img">
    <img src="{src}" srcset="{srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(exp["title"])} — Marbella" loading="lazy" width="600" height="375">
    {tag_html}
  </div>
  <div class="boat-card-body">
    <h3 class="boat-card-title">{html.escape(exp["title"])}</h3>
    <p class="boat-card-desc">{html.escape(exp["desc"])}</p>
    <div class="boat-card-meta">
      <span class="boat-card-price">From <strong>€{exp["from"]}</strong><small>see page</small></span>
      <span class="boat-card-cta">Explore →</span>
    </div>
  </div>
</a>'''

# ---------- shared writer ----------
def write_page(slug, *, title, meta, h1, sub, eyebrow, body_html_str, jsonld, breadcrumbs, hero_base, hero_widths, hero_alt):
    url = f"{SITE['base_url']}/{slug}/"
    hero_src = f"{hero_base}-{hero_widths[-1]}.jpg"
    hero_srcset = ", ".join(f"{hero_base}-{w}.jpg {w}w" for w in hero_widths)
    repl = {
        "{{HREFLANG}}": "",
        "{{HERO_IMG}}": hero_src,
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
        "{{PRICE_LABEL}}": "2h skippered charter",
        "{{BOOK_PITCH}}": "Instant quotes from local operators across Puerto Banús, Marbella Marina, Cabopino, Estepona &amp; Sotogrande.",
        "{{BOAT_GRID}}": "",
        "{{BREADCRUMBS}}": breadcrumbs,
        "{{BODY_HTML}}": body_html_str,
        "{{VIDEO_SECTION}}": "",
        "{{GUESTS_SECTION}}": "",
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
    out_path = SITE_DIR / slug / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)

# ---------- /experiences/ hub ----------
def render_hub():
    cards = "\n".join(card_html(e) for e in EXPERIENCES)
    body = f'''<p class="byline">{len(EXPERIENCES)} experiences · Real charters, real boats from Puerto Banús</p>

<p>Marbella isn't one experience — it's many. Sunset cruises for couples, hen-party flybridges for groups of 11, fishing trips for the dads, dolphin offshore runs, day-long Gibraltar adventures. This page is the catalogue: every type of charter we run, with a price-from and a direct link to the relevant booking page.</p>

<section class="boat-grid-section" style="background:transparent;padding:24px 0 0">
  <div class="boat-grid" style="padding:0">
{cards}
  </div>
</section>

<h2>Which experience fits your group?</h2>
<ul>
  <li><strong>Couples 2:</strong> <a href="/sunset-cruise-marbella/">Sunset cruise</a> or proposal-on-a-yacht — €749 / 2 h.</li>
  <li><strong>Family with kids:</strong> <a href="/experiences/family-boat-days-marbella/">Family boat day</a> — calm-water itinerary, snacks pre-loaded, life jackets in every size.</li>
  <li><strong>Group 6–8:</strong> <a href="/boats/astondoa-40/">Astondoa 40 "Fufi"</a> day charter from €1,299 / 4 h.</li>
  <li><strong>Group 9–11 (stag/hen):</strong> <a href="/boats/azimut-39/">Azimut 39</a> flybridge, BYO welcomed, DJ add-on.</li>
  <li><strong>Group 10–12 in luxury:</strong> <a href="/boats/mangusta-80/">Mangusta 80</a> superyacht with Sea-Doo jet ski free — €4,719 / 4 h.</li>
  <li><strong>Adrenaline / solo:</strong> <a href="/jet-ski-rental-marbella/">Sea-Doo jet ski</a> at €200 / h.</li>
  <li><strong>Content creators / brands:</strong> <a href="/experiences/photoshoot-yacht-marbella/">Photoshoot day</a> — La Concha backdrop, sun-pad-ready angles.</li>
</ul>

<h2>How booking works</h2>
<ol>
  <li><strong>Browse experiences</strong> on this page or directly via <a href="/boats/">Our Boats</a>.</li>
  <li><strong>Tap "Book now"</strong> (top-right) — drops your name, WhatsApp and budget into our chat.</li>
  <li><strong>We reply in under 5 minutes</strong> with 2–3 specific boat options and the exact total.</li>
  <li><strong>30% deposit secures the date</strong> — balance the morning of the charter.</li>
  <li><strong>Show up at Puerto Banús</strong> 15 min before departure with photo ID. We'll have everything else.</li>
</ol>

<p>Not sure which experience? Just message us with "I'm in Marbella from {date.today().strftime("%-d %B")} for 3 days, what would you suggest?" — we'll send back 2–3 charter ideas tailored to your group, dates and budget.</p>'''

    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"CollectionPage",
            "name":"Marbella Boat Charter Experiences","url":SITE['base_url']+"/experiences/",
            "description":"Catalogue of charter experiences on our Marbella fleet — sunset, fishing, parties, family days, dolphin watching and more.",
            "isPartOf":{"@id":SITE['base_url']+"/#org"},
            "mainEntity":{
                "@type":"ItemList","numberOfItems":len(EXPERIENCES),
                "itemListElement":[
                    {"@type":"ListItem","position":i+1,"url":SITE['base_url']+e["slug"],"name":e["title"]}
                    for i, e in enumerate(EXPERIENCES)
                ],
            },
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Experiences","item":SITE['base_url']+"/experiences/"},
            ],
        },
    ]

    write_page(
        slug="experiences",
        title="Marbella Boat Charter Experiences: Parties, Sunset, Family, Fishing & More",
        meta="9 boat charter experiences in Marbella — sunset cruises, hen parties, family days, fishing, photoshoots, dolphin watching, Gibraltar day trips. Our fleet, our skippers, from €200.",
        h1="Marbella Boat Charter Experiences",
        sub="Sunset cruises, hen-party flybridges, family boat days, photoshoots, fishing trips, Gibraltar adventures — every Marbella charter type, with prices and direct booking.",
        eyebrow="Experiences · Marbella",
        body_html_str=body,
        jsonld=jsonld,
        breadcrumbs='<nav class="breadcrumbs"><a href="/">Home</a> › <span>Experiences</span></nav>',
        hero_base="/img/boats/mangusta-80/sun-pad",
        hero_widths=(600,900,1200),
        hero_alt="Marbella boat charter experiences — sun pad on the Mangusta 80",
    )
    print(f"  ✓ experiences hub → /experiences/")


# ---------- /experiences/family-boat-days-marbella/ ----------
def render_family():
    body = f'''<p>A family boat day in Marbella is its own type of charter — different boat choice, different itinerary, different pace from a stag-party flybridge or a sunset cruise for two. This page is the practical playbook: which of our boats works best for kids, what we pre-load on board, and where to anchor for the calmest snorkel of the day.</p>

<figure class="inline-img"><img src="/img/customers/h06-1200.jpg" srcset="/img/customers/h06-600.jpg 600w, /img/customers/h06-900.jpg 900w, /img/customers/h06-1200.jpg 1200w" sizes="(max-width: 880px) 100vw, 720px" alt="Family on board a Marbella charter yacht with kids" loading="lazy" width="1200" height="800"></figure>

<h2>Which boat for a family day?</h2>
<table>
<thead><tr><th>Family size</th><th>Boat we recommend</th><th>Why</th></tr></thead>
<tbody>
<tr><td>2 adults + 1–2 kids</td><td><a href="/boats/astondoa-40/">Astondoa 40</a></td><td>Spanish-built, classic teak interior, AC saloon, cabin for naps, gentle ride.</td></tr>
<tr><td>2 adults + 3–4 kids</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>Flybridge upstairs for the kids, AC saloon downstairs, marine head with shower.</td></tr>
<tr><td>3+ families together (10–12 guests)</td><td><a href="/boats/mangusta-80/">Mangusta 80</a></td><td>24 m of deck space — kids have their own zone, adults have theirs, jet ski included.</td></tr>
</tbody>
</table>

<h2>What's already on board for kids</h2>
<ul>
<li><strong>Life jackets in every size</strong> — infant (under 12 kg), child (12–25 kg), youth (25–40 kg), adult. Spanish maritime law requires under-12s wear them while underway; we provide.</li>
<li><strong>Snorkel masks &amp; fins</strong> in junior sizes.</li>
<li><strong>Inflatable donut + paddleboard</strong> for anchor stops.</li>
<li><strong>Bimini shade</strong> covering the cockpit (we keep kids out of direct midday sun).</li>
<li><strong>AC interior</strong> as a refuge from the heat on full-day charters.</li>
<li><strong>Marine head with shower</strong> — proper toilet, not a Porta-Potti, with running water.</li>
</ul>

<h2>What we pre-load if you ask 24 hours ahead</h2>
<ul>
<li>Fresh fruit (banana, apple, watermelon, grapes)</li>
<li>Crisps and biscuits the kids actually like (tell us brands if it matters)</li>
<li>Juice boxes (apple, orange, no high-sugar Capri-Suns by default — we go neutral)</li>
<li>Ice lollies for older kids — kept in the freezer until you ask</li>
<li>Sandwiches if you want a no-fuss lunch (€8 per child for a ham &amp; cheese + fruit + lolly box)</li>
</ul>

<h2>The calm-water itinerary (under-5s)</h2>
<ol>
<li><strong>10:00</strong> Boarding at Puerto Banús — calmer mouth in the morning, less queue.</li>
<li><strong>10:30</strong> Slow cruise east 25 min to anchor off Cabopino dunes — sandy bottom, gentle slope, sheltered from the levante.</li>
<li><strong>11:00–12:30</strong> Swim and snorkel stop. Donut launched. Kids can walk waist-deep on the sand bar.</li>
<li><strong>12:30</strong> Light lunch on board.</li>
<li><strong>13:00–13:30</strong> Naps in the cabin if needed.</li>
<li><strong>13:30</strong> Cruise back to Puerto Banús — return by 14:00, well within attention span.</li>
</ol>
<p>Total: 4 hours, €1,299. Easy half-day even with very young children.</p>

<h2>Snorkel stops worth the trip</h2>
<ul>
<li><strong>Cala Cortés (east of Cabopino)</strong> — small protected cove, 3–5 m depth, sea bream and small wrasse. Easy snorkel for 6+ year-olds.</li>
<li><strong>Río Real</strong> — sandy bottom with occasional octopus spotting near the rocks. Suits all ages.</li>
<li><strong>Cala del Faro (west of Estepona)</strong> — rockier, deeper. Better for confident swimmers 9+.</li>
</ul>

<h2>Safety basics that come up</h2>
<ul>
<li><strong>UV doubles at sea</strong> — reflection off the water. UPF 50 rash vest + hat + 50+ sunscreen is non-negotiable.</li>
<li><strong>Engine zone is off-limits</strong> while running — skipper will brief the kids in 30 seconds before departure.</li>
<li><strong>Bare feet on deck</strong> — better grip than any shoe on wet teak.</li>
<li><strong>Marine life</strong> — Marbella waters are benign. No jellyfish bloom most years, no aggressive fish. Watch for sea urchins at rocky entries (Cabopino dunes is sandy so safe).</li>
</ul>

<h2>How to book a family day</h2>
<p>Tap <strong>Book now</strong> top-right — tell us how many adults + kids, ages of the kids, your date and rough budget. We reply with 2–3 specific boats and the exact total. 30% deposit secures the date, balance the morning of the charter. Free cancellation up to 7 days out; weather cancellations 100% refunded.</p>

<p>For the full guide on charting with kids in Marbella (life-jacket rules, packing list, things that go wrong), see our <a href="/blog/kids-on-a-boat-marbella/">kids on a boat in Marbella</a> blog post.</p>

<h2>Frequently asked questions</h2>
<details><summary>What's the minimum age for a family charter?</summary><p>No legal minimum, but operators recommend 6 months and above. Babies under 6 months struggle with the sun and motion on most boats. From 1 year up, with the right boat and a short morning itinerary, kids do brilliantly.</p></details>
<details><summary>Do you provide life jackets for kids?</summary><p>Yes, in every size — infant (under 12 kg), child (12–25 kg), youth (25–40 kg), and adult. Spanish maritime law requires under-12s wear them while underway. Mention any unusual sizing when booking.</p></details>
<details><summary>Can we bring our own food?</summary><p>Yes — BYO welcomed for snacks, sandwiches, fruit. We also pre-load on request with 24 h notice. Catered lunches (paella, sushi platter, hot meals) are €25–€60 per head.</p></details>
<details><summary>How long can young kids cope on a boat?</summary><p>Under-3s: 2–3 hours total. 4–7s: 3–4 hours comfortably (longer with naps in the cabin). 8+: full day works if there's a swim stop and snacks. Build in shade — bimini covers the cockpit, but the foredeck is sun-exposed.</p></details>
<details><summary>What if the kids get seasick?</summary><p>Mention it when booking and the skipper picks a calm-water route (Marbella Marina to Cabopino in the morning is virtually flat). Ginger biscuits help. If symptoms appear, we anchor in the calmest spot immediately. Catamarans and motor yachts both have flat-deck stability that minimises motion.</p></details>'''

    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"Service",
            "name":"Family Boat Day Marbella",
            "url":SITE['base_url']+"/experiences/family-boat-days-marbella/",
            "provider":{"@id":SITE['base_url']+"/#org"},
            "areaServed":"Marbella, Spain",
            "audience":{"@type":"PeopleAudience","name":"Families with children"},
            "offers":{"@type":"AggregateOffer","priceCurrency":"EUR","lowPrice":SITE['price_anchor_low_2h'],"highPrice":SITE['price_anchor_fullday_8h']},
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Experiences","item":SITE['base_url']+"/experiences/"},
                {"@type":"ListItem","position":3,"name":"Family Boat Days","item":SITE['base_url']+"/experiences/family-boat-days-marbella/"},
            ],
        },
    ]

    write_page(
        slug="experiences/family-boat-days-marbella",
        title="Family Boat Days in Marbella: Kids, Snorkel & Calm-Water Itineraries",
        meta="Family boat charter Marbella from €749 — calm-water routes, snorkel stops at Cabopino & Cala Cortés, life jackets in every size, snacks pre-loaded. Astondoa 40 & Azimut 39.",
        h1="Family Boat Days in Marbella",
        sub="Calm-water itineraries, snorkel stops, snacks pre-loaded for the kids — Astondoa 40, Azimut 39 or Mangusta 80 depending on your group.",
        eyebrow="Family · Marbella",
        body_html_str=body,
        jsonld=jsonld,
        breadcrumbs='<nav class="breadcrumbs"><a href="/">Home</a> › <a href="/experiences/">Experiences</a> › <span>Family Boat Days</span></nav>',
        hero_base="/img/boats/astondoa-40/hero",
        hero_widths=(600,900,1200,1600),
        hero_alt="Family boat day in Marbella — Astondoa 40 charter for families with kids",
    )
    print("  ✓ /experiences/family-boat-days-marbella/")


# ---------- /experiences/photoshoot-yacht-marbella/ ----------
def render_photoshoot():
    body = f'''<p>A yacht photoshoot in Marbella is its own kind of charter — different goals from a sunset cruise or a stag party. Models or photographers want light angles, deck space, backdrop options. This page is the practical guide: which boat shoots best, what time of day works, where to anchor for the iconic La Concha shot, and how to coordinate hair / makeup / outfit changes on board.</p>

<figure class="inline-img"><img src="/img/customers/h04-1200.jpg" srcset="/img/customers/h04-600.jpg 600w, /img/customers/h04-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Photoshoot on a Marbella yacht — guest at the helm in a white dress" loading="lazy" width="1200" height="800"></figure>

<h2>Best boat for a photoshoot</h2>
<table>
<thead><tr><th>Shoot type</th><th>Boat we recommend</th><th>Why</th></tr></thead>
<tbody>
<tr><td>Single model / influencer reels</td><td><a href="/boats/astondoa-40/">Astondoa 40 "Fufi"</a></td><td>Teak detailing, cream leather, Spanish flag — Mediterranean aesthetic. €749 / 2 h.</td></tr>
<tr><td>Fashion shoot, multiple looks</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>Two cabins for changing, AC saloon for hair / makeup, real flybridge with second background option.</td></tr>
<tr><td>Brand campaign, lifestyle / luxury</td><td><a href="/boats/mangusta-80/">Mangusta 80 "Nina"</a></td><td>24 m of deck = unlimited angles. Sun-pad foredeck, marble galley, separate aft seating, jet ski for action shots. €4,719 / 4 h.</td></tr>
</tbody>
</table>

<h2>The 5 iconic Marbella backdrop angles</h2>
<ol>
<li><strong>La Concha mountain</strong> — the most recognizable Marbella backdrop. Anchor anywhere between Puerto Banús and Marbella Marina, shoot with the boat oriented so the mountain is to the model's right shoulder. Best 10:00–12:00 when the mountain is in full sun.</li>
<li><strong>Puerto Banús superyacht line</strong> — exit the marina, then circle back so the 50 m+ yachts are behind. Shoot from the bow looking back. Best at the start or end of the charter.</li>
<li><strong>Open Mediterranean with no land visible</strong> — perfect for "no horizon line" pre-set looks. Anchor 2 NM offshore (calm-water mornings).</li>
<li><strong>Golden hour Golden Mile</strong> — last 90 min before sunset. Boat positioned 200 m off the coast, low sun behind the model, Marbella Club and Puente Romano in the background.</li>
<li><strong>Sea-Doo action</strong> — for adrenaline brand shoots. The skipper drives a chase boat alongside the jet ski. Mangusta 80 charter includes the Sea-Doo free.</li>
</ol>

<h2>Light timing</h2>
<p>Marbella sits 36.5°N. In peak summer the sun crosses overhead between 13:30 and 14:30 — harsh light, hard shadows. Avoid this window if you want soft, cinematic footage. Best windows:</p>
<ul>
<li><strong>09:00–11:00</strong> — soft light, calmer sea, fewer boats on the water. Best for editorial / fashion.</li>
<li><strong>16:00–18:00</strong> — warmer tones, the levante usually drops in the afternoon. Best for lifestyle / drone shots.</li>
<li><strong>19:00–21:00 (Jun–Sep)</strong> — golden hour and blue hour. Best for romantic / aspirational stills.</li>
</ul>
<p>For sunset specifically, see our <a href="/sunset-cruise-marbella/">sunset cruise page</a> — same windows apply.</p>

<h2>What we set up for the shoot</h2>
<ul>
<li><strong>The boat without our branding visible</strong> — no signage, no Fufi-emblazoned towels in the frame unless you want them.</li>
<li><strong>Tidy deck</strong> — fenders stowed, lines coiled, no operational clutter visible to the camera.</li>
<li><strong>Power outlets</strong> — for charging cameras, hair tools, ring lights. 220 V Spanish sockets on board.</li>
<li><strong>Mirror &amp; AC interior</strong> — saloon doubles as a makeup room.</li>
<li><strong>Towels / robes for between shots</strong> — water and wind dry hair fast.</li>
<li><strong>Drone-friendly skipper</strong> — comfortable manoeuvring for top-down drone passes if you've brought a pilot.</li>
</ul>

<h2>Drone footage from the boat</h2>
<p>Spain allows commercial drone flying with a registered Spanish operator (AESA-registered, with insurance). Casual recreational flying from a charter is grey-zone — fine if you stay under 120 m, line of sight, away from marinas. We can't fly a drone for you but we can position the boat for drone passes if you've brought your own pilot. For best top-down sun-pad shots, anchor offshore in flat water around 11:00 — the boat is stationary, no wake, easy framing.</p>

<h2>Wardrobe + makeup logistics</h2>
<p>The Mangusta 80 has the most space for outfit changes — three cabins, separate heads, marble countertop in the galley for makeup. The Astondoa 40 has one master cabin + a guest cabin (enough for 2 looks). The Azimut 39 has two cabins (enough for 3-4 looks). Bring outfits on hangers (not folded) — there's a small wardrobe in each cabin.</p>

<h2>Booking and pricing</h2>
<p>Same prices as a regular charter — no "photoshoot upcharge". The €749 / 2 h Astondoa or Azimut works for influencer reels. The €4,719 / 4 h Mangusta works for fashion campaigns or brand shoots where you need real luxury aesthetic. Half-day or full-day rates available — see <a href="/boats/">our boats</a> for the full grid.</p>

<p>Tap <strong>Book now</strong> top-right and tell us your shoot type, dates, and any specific shots you want (e.g. "La Concha sunset", "drone top-down on sun-pad", "Sea-Doo action"). We'll match the right boat and time of day.</p>

<h2>Frequently asked questions</h2>
<details><summary>Can you remove your branding from the boat for the shoot?</summary><p>Yes. The boat name on the stern is permanent (we can't repaint), but we'll stow any "Boat Rental Marbella" towels, banners or branded items. The boat looks like a private yacht in the photos.</p></details>
<details><summary>Can the skipper drive the boat for action shots?</summary><p>Yes — fast cruising, tight turns for wake shots, anchoring in specific spots. Just brief the skipper before departure. We won't do anything that creates a real safety hazard (we don't do dangerously close passes between boats).</p></details>
<details><summary>Do you provide a photographer?</summary><p>No — bring your own. We can recommend Marbella-based photographers we've worked with if you ask. The boat plus skipper plus drinks plus deck space is what we provide.</p></details>
<details><summary>What about hair and makeup on board?</summary><p>The AC saloon doubles as a hair / makeup space. Bring your own tools — there's 220 V power. For a full HMUA team on board, book the Mangusta 80 (more space) or arrive at the dock already prepped.</p></details>
<details><summary>Can we shoot at sunset?</summary><p>Yes — the 2-hour sunset slot (departing 75 min before official sunset) is one of our most popular shoots. Same €749 price as any 2 h charter. Read more on <a href="/sunset-cruise-marbella/">sunset cruise Marbella</a>.</p></details>'''

    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"Service",
            "name":"Yacht Photoshoot Marbella",
            "url":SITE['base_url']+"/experiences/photoshoot-yacht-marbella/",
            "provider":{"@id":SITE['base_url']+"/#org"},
            "areaServed":"Marbella, Spain",
            "audience":{"@type":"PeopleAudience","name":"Photographers, influencers, brands"},
            "offers":{"@type":"AggregateOffer","priceCurrency":"EUR","lowPrice":SITE['price_anchor_low_2h'],"highPrice":SITE['price_anchor_fullday_8h']},
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Experiences","item":SITE['base_url']+"/experiences/"},
                {"@type":"ListItem","position":3,"name":"Photoshoot on a Yacht","item":SITE['base_url']+"/experiences/photoshoot-yacht-marbella/"},
            ],
        },
    ]

    write_page(
        slug="experiences/photoshoot-yacht-marbella",
        title="Photoshoot on a Yacht in Marbella: Light, Angles, Backdrops",
        meta="Marbella yacht photoshoot from €749 — Astondoa 40, Azimut 39 or Mangusta 80 superyacht. La Concha mountain backdrop, golden-hour windows, drone-friendly skippers, AC interior for changes.",
        h1="Photoshoot on a Yacht in Marbella",
        sub="The iconic La Concha backdrop, golden-hour windows, drone-friendly skippers — and an AC saloon doubling as a hair / makeup room.",
        eyebrow="Photoshoot · Marbella",
        body_html_str=body,
        jsonld=jsonld,
        breadcrumbs='<nav class="breadcrumbs"><a href="/">Home</a> › <a href="/experiences/">Experiences</a> › <span>Photoshoot on a Yacht</span></nav>',
        hero_base="/img/boats/mangusta-80/sun-pad",
        hero_widths=(600,900,1200),
        hero_alt="Marbella yacht photoshoot — sun pad on the Mangusta 80",
    )
    print("  ✓ /experiences/photoshoot-yacht-marbella/")


# ---------- /experiences/bachelor-hen-parties-marbella/ ----------
def render_bachelor_hen():
    body = f'''<p>Marbella has a specific Sunday script for bachelor and hen weekends — and the yacht charter is the anchor activity. This page is the practical playbook: which boat fits which group size, the standard 4-hour itinerary that builds the whole day, BYO rules, DJ add-ons, and how to coordinate the beach-club tender so you arrive when the day is already going.</p>

<figure class="inline-img"><img src="/img/customers/h02-1200.jpg" srcset="/img/customers/h02-600.jpg 600w, /img/customers/h02-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Hen party on a Marbella yacht charter" loading="lazy" width="1200" height="800"></figure>

<h2>Best boat for the group size</h2>
<table>
<thead><tr><th>Group</th><th>Boat</th><th>Price (4 h half-day)</th></tr></thead>
<tbody>
<tr><td>6–8 guests</td><td><a href="/boats/astondoa-40/">Astondoa 40</a></td><td>€1,299 — €162 per head</td></tr>
<tr><td>9–11 guests (hen + stag sweet spot)</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>€1,299 — €118 per head</td></tr>
<tr><td>10–12 luxury</td><td><a href="/boats/mangusta-80/">Mangusta 80</a></td><td>€4,719 — €393 per head, jet ski included</td></tr>
</tbody>
</table>
<p>For groups over 12 we split into two boats and synchronise itineraries — same price per boat, both arriving at Cabopino together.</p>

<h2>The standard 4-hour script</h2>
<ol>
<li><strong>14:00 — Boarding at Puerto Banús</strong>. Welcome drinks, photos at the pontoon. Ice tubs already chilled.</li>
<li><strong>14:30 — Cast off</strong>. Slow cruise west past Marbella Club and Puente Romano. The Golden Mile mansions are part of the show.</li>
<li><strong>15:15 — Anchor stop at Río Verde</strong>. Swim, donut, paddleboard. Music up. This is where the day actually starts.</li>
<li><strong>16:30 — Optional beach-club tender</strong> to Nikki Beach or Ocean Club. You spend 90 min ashore, pay entry separately (€50–€150 minimum spend per head), then we collect you. Or skip and continue east to Cabopino.</li>
<li><strong>17:30 — Return cruise to Puerto Banús</strong>. Slow lap of the harbour mouth for photos.</li>
<li><strong>18:00 — Disembark</strong>. Taxis or walk to dinner at Antonio's or Tikitano.</li>
</ol>

<h2>What's included vs paid extras</h2>
<p><strong>Included in the €749 / €1,299 / €4,719 price:</strong> licensed skipper, fuel, water, soft drinks, beer, white wine, cava, light snacks (crisps, almonds, fruit), insurance, VAT, ice tubs, snorkel masks, inflatable donut and paddleboard, Bluetooth sound system.</p>
<p><strong>Common paid extras:</strong></p>
<ul>
<li><strong>Pro DJ + speaker system upgrade</strong> — €350 half-day, €600 full day.</li>
<li><strong>Live saxophonist on the boat</strong> — €400–€600.</li>
<li><strong>Catered platters</strong> (sushi, charcuterie, paella) — €25–€80 per head, 24 h notice.</li>
<li><strong>Premium spirits</strong> — bring your own (cava is included; vodka, tequila, gin are BYO).</li>
<li><strong>Photographer on board</strong> — €200 / hour, we can recommend one.</li>
<li><strong>Beach club entry</strong> — paid separately at the club, €50–€150 minimum per head.</li>
<li><strong>Jet ski hour</strong> — €200 (free on Mangusta 80 charter).</li>
</ul>

<h2>BYO rules</h2>
<ul>
<li><strong>Yes:</strong> bring your own spirits, mixers, beer top-ups, additional cava, snacks, costume pieces, inflatable swans, music playlists, decorations.</li>
<li><strong>Cans and plastic only on deck</strong> — no glass. Spanish marina fines for broken glass overboard are punishing and we enforce this.</li>
<li><strong>No confetti, no glitter</strong> — anything that ends up in the water is a problem.</li>
<li><strong>No open flames</strong> — no shisha, no candles, no cake-candle photo moments unless we coordinate ashore.</li>
<li><strong>Drugs are an instant return-to-port</strong> — security deposit forfeit. Don't.</li>
</ul>

<h2>Best months for stag &amp; hen</h2>
<p>Late June through early September is the season. Sea is 22–24 °C, the marina scene is at full volume, beach clubs are in peak operation. <strong>July</strong> is the busiest single month — book 4 weeks ahead for Saturday slots. <strong>Mid-September</strong> keeps the warmth and drops prices 10–15% — best value for groups happy with a slightly quieter scene. Avoid Saturday in August if you want last-minute availability.</p>

<h2>Booking and deposit</h2>
<p>Tap <strong>Book now</strong> top-right. Tell us:</p>
<ul>
<li>Date (or weekend range)</li>
<li>Group size</li>
<li>Hen or stag — and how rowdy (we'll match the right skipper)</li>
<li>Half-day vs full-day preference</li>
<li>BYO vs paid bar preference</li>
<li>DJ + beach-club tender if you want them</li>
</ul>
<p>We respond within 5 min on WhatsApp with 2–3 specific boats + itemised quote. 30% deposit secures, balance morning of charter. Free cancellation up to 7 days out; weather cancellations 100% refunded.</p>

<h2>Frequently asked questions</h2>
<details><summary>Can we bring our own alcohol?</summary><p>Yes on private charters — BYO is welcomed. Cava, beer, white wine are already on board free. Spirits and mixers you bring yourself. Cans and plastic only on deck — no glass.</p></details>
<details><summary>What about the beach-club tender?</summary><p>The skipper anchors offshore from Nikki Beach or Ocean Club, then tenders the group ashore in the dinghy or jet-ski (4 at a time). You spend 90 min at the club, pay club entry separately, then we collect. Standard add-on, no extra boat charge.</p></details>
<details><summary>Will the skipper join the party?</summary><p>The skipper stays sober and at the helm — that's their job under Spanish maritime law. But they're friendly, take photos, and most have done hundreds of stag/hen days. Tip is appreciated (€50–€100 cash for a great half-day).</p></details>
<details><summary>What if the weather is bad?</summary><p>If forecast wind exceeds Force 4–5 (~20+ knots) the skipper postpones the night before. You re-book a date or get 100% refund. Light rain alone is not a cancellation reason in Marbella.</p></details>
<details><summary>Can we split the group across two boats?</summary><p>Yes — common for groups of 14+. We synchronise itineraries so both boats anchor at the same spots. Each boat is its own booking at its own price.</p></details>'''

    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"Service",
            "name":"Bachelor & Hen Party Charter Marbella",
            "url":SITE['base_url']+"/experiences/bachelor-hen-parties-marbella/",
            "provider":{"@id":SITE['base_url']+"/#org"},
            "areaServed":"Marbella, Spain",
            "audience":{"@type":"PeopleAudience","name":"Bachelor and hen party groups"},
            "offers":{"@type":"AggregateOffer","priceCurrency":"EUR","lowPrice":SITE['price_anchor_low_2h'],"highPrice":SITE['price_anchor_fullday_8h']},
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Experiences","item":SITE['base_url']+"/experiences/"},
                {"@type":"ListItem","position":3,"name":"Bachelor & Hen Parties","item":SITE['base_url']+"/experiences/bachelor-hen-parties-marbella/"},
            ],
        },
    ]

    write_page(
        slug="experiences/bachelor-hen-parties-marbella",
        title="Bachelor & Hen Party Yacht Charter Marbella: Full Day Script",
        meta="Bachelor & hen party yacht charter Marbella — Azimut 39 (11 guests), Mangusta 80 (12 guests). BYO welcomed, DJ add-on, beach-club tender. From €1,299 / 4 h.",
        h1="Bachelor & Hen Parties in Marbella",
        sub="The Sunday script for hen and stag weekends — yacht morning, beach-club tender, sunset return. Groups 9–12 guests, BYO welcomed.",
        eyebrow="Bachelor & Hen · Marbella",
        body_html_str=body,
        jsonld=jsonld,
        breadcrumbs='<nav class="breadcrumbs"><a href="/">Home</a> › <a href="/experiences/">Experiences</a> › <span>Bachelor & Hen Parties</span></nav>',
        hero_base="/img/customers/h02",
        hero_widths=(400,600,900),
        hero_alt="Bachelor and hen party yacht charter in Marbella",
    )
    print("  ✓ /experiences/bachelor-hen-parties-marbella/")


# ---------- Tier-1 batch — render via a generic helper ----------
def render_tier1(slug, title, meta, h1, sub, eyebrow, body_html_str, hero_base, hero_widths, hero_alt, audience, breadcrumb_name):
    jsonld = [
        jsonld_org(),
        {
            "@context":"https://schema.org","@type":"Service",
            "name": title,
            "url": SITE['base_url']+f"/{slug}/",
            "provider":{"@id":SITE['base_url']+"/#org"},
            "areaServed":"Marbella, Spain",
            "audience":{"@type":"PeopleAudience","name":audience},
            "offers":{"@type":"AggregateOffer","priceCurrency":"EUR","lowPrice":SITE['price_anchor_low_2h'],"highPrice":SITE['price_anchor_fullday_8h']},
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Experiences","item":SITE['base_url']+"/experiences/"},
                {"@type":"ListItem","position":3,"name":breadcrumb_name,"item":SITE['base_url']+f"/{slug}/"},
            ],
        },
    ]
    write_page(
        slug=slug,
        title=title, meta=meta, h1=h1, sub=sub, eyebrow=eyebrow,
        body_html_str=body_html_str, jsonld=jsonld,
        breadcrumbs=f'<nav class="breadcrumbs"><a href="/">Home</a> › <a href="/experiences/">Experiences</a> › <span>{html.escape(breadcrumb_name)}</span></nav>',
        hero_base=hero_base, hero_widths=hero_widths, hero_alt=hero_alt,
    )
    print(f"  ✓ /{slug}/")


# ---------- Tier-1 page bodies ----------
def render_wedding():
    body = '''<p>A wedding on a yacht in Marbella is the rarest charter we run — usually one Saturday per high-season month — and the most logistically rich. This page covers the actual playbook: which boat for the ceremony vs the reception, whether you need a registrar on board (mostly no — see below), how we coordinate the photographer's shot list, and what the day actually looks like start-to-finish.</p>

<figure class="inline-img"><img src="/img/customers/h04-1200.jpg" srcset="/img/customers/h04-600.jpg 600w, /img/customers/h04-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Wedding on a yacht in Marbella — bride at the helm in a white dress" loading="lazy" width="1200" height="800"></figure>

<h2>The legal piece (read this first)</h2>
<p>A wedding ceremony on a Spanish-flagged charter yacht is <strong>not legally binding in Spain</strong> unless you've completed the civil paperwork ashore beforehand. What most couples do: complete the civil registration at Marbella town hall a few days earlier (treat as a paperwork formality), then do the actual ceremony on board with a celebrant, family, friends — the day everyone remembers. Religious / symbolic-only ceremonies on board are common and need no paperwork. Tell us which route you want when you enquire.</p>

<h2>Best boat for a wedding</h2>
<table>
<thead><tr><th>Wedding size</th><th>Boat</th><th>Notes</th></tr></thead>
<tbody>
<tr><td>Couple + 4–6 closest people (elopement)</td><td><a href="/boats/astondoa-40/">Astondoa 40 "Fufi"</a></td><td>Intimate. Teak and cream interior, one ceremony spot on the bow. €749 / 2h.</td></tr>
<tr><td>Up to 11 guests</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>Flybridge for the ceremony, saloon for the reception. €749 / 2h.</td></tr>
<tr><td>12 guests, full luxury reception</td><td><a href="/boats/mangusta-80/">Mangusta 80 "Nina"</a></td><td>Marble galley supports a proper catered reception. Sea-Doo for the post-vows fun. €4,719 / 4h.</td></tr>
<tr><td>20–30 guests (two boats)</td><td>Azimut 39 + Astondoa 40 in tandem</td><td>Both anchor side-by-side at Río Verde for the ceremony, separate reception spaces. Quoted on WhatsApp.</td></tr>
</tbody>
</table>

<h2>The day, hour-by-hour</h2>
<ol>
<li><strong>12:00 — Hair and makeup ashore</strong> at the hotel (Don Carlos, Marbella Club, Puente Romano common). We'll coordinate transfer.</li>
<li><strong>14:30 — Boarding at Puerto Banús</strong> with the wedding party + photographer. Champagne welcome, white-rose decoration we've pre-loaded.</li>
<li><strong>15:00 — Cast off</strong>, slow cruise to the ceremony anchorage (Río Verde or Cala del Faro, picked the morning of based on wind).</li>
<li><strong>15:30 — Anchor and ceremony</strong>. Bow set up with the celebrant. Music via the on-board system (sent us your processional + recessional 24h before).</li>
<li><strong>16:00 — Group photos</strong> at La Concha and the swim platform.</li>
<li><strong>16:30 — Reception begins.</strong> Cava + canapés we've coordinated with the catering team.</li>
<li><strong>18:00 — First dance on the flybridge</strong>. Couple-only swim if you want it.</li>
<li><strong>19:30 — Return to Puerto Banús</strong>, met by transfers to the dinner venue.</li>
</ol>

<h2>What we coordinate vs what you bring</h2>
<p><strong>We coordinate:</strong> the boat, skipper, fuel, drinks (cava + wine + beer on board), light snacks, anchor location selection (wind-aware), basic deck flowers/runner if you ask. Standard inclusions apply.</p>
<p><strong>You coordinate (we recommend vendors):</strong> celebrant or registrar, hair / makeup, photographer / videographer (your own or a Marbella name we can recommend), wedding cake, catered hot food, DJ for any after-party ashore, hotel and transfers.</p>

<h2>Marbella wedding photographers we've shot with</h2>
<p>We don't take a cut and we don't sell photography. But the wedding photographers who deliver consistently good Marbella yacht shoots tend to be: Spanish-based shooters who know the light (sun angle drops fast after 17:00 in spring/autumn), have shot with our crew before (they know the boat's best angles), and bring a second shooter for the dock + reception split. Ask us for a current shortlist when you enquire — we update it every season.</p>

<h2>Pricing example</h2>
<p>Typical small-wedding all-in (boat + crew + drinks-on-board + light deck dressing, on the Azimut 39 for 8 guests + couple, 4-hour charter): <strong>€1,299</strong>. Add a catered cocktail-hour reception (€55/head x 10) = €1,849. Plus your photographer, celebrant, dinner ashore, hotel. Bigger weddings on the Mangusta 80 start around €4,719 for the boat alone.</p>

<h2>Booking and lead time</h2>
<p>Wedding bookings: <strong>3–6 months ahead</strong> for July/August Saturdays. Off-season (Oct–May): often available 4 weeks ahead. 30% deposit secures the date, balance 14 days before. Weather backup plan: we always identify a Plan-B date 1 week later when you book. Weather-cancelled weddings get 100% refund or free reschedule.</p>

<p>Tap <strong>Book now</strong> top-right with date, party size, ceremony / reception split, and which boat you've shortlisted. We respond within 30 min during business hours with a full quote and timeline.</p>

<h2>Frequently asked questions</h2>
<details><summary>Can we legally get married on the yacht?</summary><p>The ceremony on the boat is not legally binding in Spain by itself — you complete the civil registration at Marbella town hall beforehand (treat as paperwork), then the on-board ceremony is the actual celebration. Religious or symbolic-only ceremonies need no paperwork.</p></details>
<details><summary>Do you provide a celebrant?</summary><p>No — we can recommend Marbella-based bilingual celebrants (English / Spanish, sometimes French). Or you bring your own from home. The celebrant's fee is separate from the charter.</p></details>
<details><summary>What if the weather is bad?</summary><p>The skipper assesses the night before. If forecast wind exceeds Force 4–5 or sea state makes the ceremony unsafe / uncomfortable, we reschedule to the Plan-B date we agreed at booking, or refund 100%. No partial-fee fights.</p></details>
<details><summary>Can we bring our own cake / catering?</summary><p>Yes. We're charter, not catering — most weddings bring an external chef or catering team. We coordinate dock-side pickup and on-board service. Catered platters (€55–€80/head) can also be arranged through our partner caterers.</p></details>
<details><summary>How many guests can come?</summary><p>Up to 12 on the Mangusta 80, 11 on the Azimut 39, 9 on the Astondoa 40. For 20–30 guests, we use two boats in tandem. For larger weddings, the ceremony happens on the boat and the reception moves ashore.</p></details>'''
    render_tier1(
        slug="experiences/wedding-yacht-marbella",
        title="Wedding on a Yacht in Marbella: Boats, Logistics, Legal Note",
        meta="Wedding yacht charter Marbella — ceremony on a flybridge under La Concha, reception with cava on board, photo coordination. Astondoa 40, Azimut 39 or Mangusta 80. From €1,299.",
        h1="Wedding on a Yacht in Marbella",
        sub="Ceremony at anchor, reception under La Concha, the photo set everyone screenshots — the full Marbella yacht-wedding playbook.",
        eyebrow="Wedding · Marbella",
        body_html_str=body,
        hero_base="/img/customers/h04",
        hero_widths=(400,600,900),
        hero_alt="Wedding on a yacht in Marbella",
        audience="Wedding couples and parties",
        breadcrumb_name="Wedding on a Yacht",
    )


def render_corporate():
    body = '''<p>Corporate yacht charters in Marbella sit in a different lane to private bookings — they need invoiced VAT receipts, a sober skipper who can host C-level clients, often a dual-language briefing (English + Spanish or English + Russian), and a calendar that handles last-minute movement. This page is the operator-level brief: what we run for incentive teams, board off-sites, client hosting, and team-building days from Puerto Banús.</p>

<figure class="inline-img"><img src="/img/boats/mangusta-80/saloon-1200.jpg" srcset="/img/boats/mangusta-80/saloon-600.jpg 600w, /img/boats/mangusta-80/saloon-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Mangusta 80 saloon set up for a corporate yacht charter in Marbella" loading="lazy" width="1200" height="800"></figure>

<h2>Use cases we run regularly</h2>
<ul>
<li><strong>Client hosting:</strong> half-day cruise with key accounts. Lunch on board (catered), drinks, dock-side meeting room before/after.</li>
<li><strong>Sales kick-off / off-site:</strong> mid-week half-day for the leadership team — change of setting, board-room-style flybridge, then dinner ashore.</li>
<li><strong>Incentive trip:</strong> reward the top 10–20 reps. Run as one boat with shifts, or two boats in parallel.</li>
<li><strong>Team building:</strong> the active version (snorkel, jet ski rotation, paddleboard race) or the quiet version (cruise + facilitated conversation + lunch).</li>
<li><strong>Conference side-event:</strong> agencies booking yachts during conferences at Marbella Convention Centre, Don Pepe, Marbella Club.</li>
<li><strong>Influencer / brand activation day:</strong> hosted media on a flagship yacht, content captured.</li>
</ul>

<h2>Best boat for size + budget</h2>
<table>
<thead><tr><th>Group</th><th>Boat</th><th>Half-day (4 h)</th></tr></thead>
<tbody>
<tr><td>Up to 9 (small board / VIP clients)</td><td><a href="/boats/astondoa-40/">Astondoa 40</a></td><td>€1,299</td></tr>
<tr><td>10–11 (extended team)</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>€1,299</td></tr>
<tr><td>12 in luxury (flagship client hosting)</td><td><a href="/boats/mangusta-80/">Mangusta 80</a></td><td>€4,719 (jet ski included)</td></tr>
<tr><td>20–24 (two boats parallel)</td><td>Two boats from the fleet</td><td>Quoted on WhatsApp</td></tr>
<tr><td>30+ (multiple boats, coordinated)</td><td>Three+ boats</td><td>Quoted on WhatsApp</td></tr>
</tbody>
</table>

<h2>Invoicing, VAT, and procurement</h2>
<p>All charters are invoiced from our Spanish company with full Spanish IVA (21%) — claimable for EU-based companies under standard VAT recovery. Invoice issued the day of charter, payable up to 30 days net for known corporate clients (50% deposit at booking for new clients). We accept bank transfer (preferred for corporate accounts), card payment, and we can quote in EUR / GBP / USD for accounting purposes. Send purchase orders to <a href="mailto:hello@boatrentalinmarbella.com">hello@boatrentalinmarbella.com</a>.</p>

<h2>Team-building activity menu</h2>
<p>Pick from these — combine as many as fit your timeframe:</p>
<ul>
<li><strong>Snorkel + paddleboard rotation</strong> at Cala del Faro — 4 stations, 15 min each, team scoring. 90 min total.</li>
<li><strong>Jet ski circuit</strong> (Mangusta 80 charters get one free; others €200/hour) — relay-style or solo time-trial.</li>
<li><strong>Anchored lunch with facilitator</strong> — bring your own facilitator or we recommend a local one. Plenary on the flybridge.</li>
<li><strong>Race the route</strong> — two boats race a coastal triangle. Skippers compete on time-elapsed, team competes on tasks at each waypoint.</li>
<li><strong>Photography challenge</strong> — guests get the brief at boarding, judging at sunset. Works well with mixed-experience teams.</li>
<li><strong>Cooking on board</strong> — paella class on the Mangusta 80 galley with a visiting chef. €600 chef fee + ingredients.</li>
</ul>

<h2>Standard inclusions (every corporate charter)</h2>
<ul>
<li>Licensed skipper for the full duration</li>
<li>Fuel for the coastal route</li>
<li>Water, soft drinks, beer, white wine, cava</li>
<li>Light snacks (fruit, crisps, almonds)</li>
<li>Insurance &amp; safety equipment</li>
<li>Spanish IVA (21%) invoiced</li>
<li>Snorkel masks, donut, paddleboard</li>
<li>Towels for every guest</li>
</ul>
<p>Common paid extras: catered lunch (€25–€80/head), DJ + sound upgrade (€350), professional photographer (€200/h), GoPros for capture, brand banners hung on the bow.</p>

<h2>Compliance + safety brief</h2>
<p>For corporate insurance and HR teams: every boat carries third-party liability + passenger insurance. Skippers hold PER or higher licence. Pre-charter safety briefing covers life jackets, swim zone, jet ski rules, alcohol policy (we limit serving for very young teams or known liability cases — flag in advance). We can sign NDAs and provide certificates of insurance on request.</p>

<h2>Booking + lead time</h2>
<p>For peak July-August Fridays: 6–8 weeks ahead. Mid-week or shoulder-season: 2–3 weeks. Same-week last-minute bookings happen mid-week in May/Sept. Email or WhatsApp with: company name, date(s), party size, half-day or full-day, language preference, any specific itinerary or facilitator requests.</p>

<p>For procurement questions, ask for a formal proposal — we send within 24 hours with itemised quote, invoice template, and skipper bios.</p>

<h2>Frequently asked questions</h2>
<details><summary>Can we get a VAT-deductible invoice?</summary><p>Yes — all charters invoice with Spanish IVA at 21%, recoverable under EU VAT rules for EU companies. Non-EU companies receive the gross-of-VAT invoice; reclaim depends on your jurisdiction.</p></details>
<details><summary>Do you sign NDAs?</summary><p>Yes — we routinely sign mutual NDAs for client hosting where guest identities are sensitive. Send the NDA at booking; we review within 48 hours.</p></details>
<details><summary>Can the skipper speak our team's language?</summary><p>All skippers speak fluent English and Spanish. We have skippers who additionally speak French, Italian, Russian, and Arabic — request the language at booking.</p></details>
<details><summary>What's the minimum group size?</summary><p>No minimum — the Astondoa 40 takes 1 person at the same €749 / 2h price as 9 guests. For board-of-two client lunches, that's the right boat.</p></details>
<details><summary>Can we run a multi-day off-site?</summary><p>Yes — overnight stays on the Mangusta 80, multi-day with shore accommodation at Don Carlos / Marbella Club. Quoted bespoke.</p></details>
<details><summary>Do you carry corporate insurance?</summary><p>Yes — €1.5M third-party + passenger liability per charter. Certificate of insurance available on request.</p></details>'''
    render_tier1(
        slug="experiences/corporate-yacht-marbella",
        title="Corporate Yacht Charter Marbella: Team Building, Client Hosting & Off-Sites",
        meta="Corporate yacht charter Marbella — invoiced with Spanish IVA, board off-sites, client hosting, team building. Up to 24 guests across two boats. Half-day from €1,299.",
        h1="Corporate Yacht Charter in Marbella",
        sub="Team off-sites, client hosting, incentive days — invoiced with full Spanish IVA, NDAs signed, skippers fluent in EN/ES/FR/IT/RU.",
        eyebrow="Corporate · Marbella",
        body_html_str=body,
        hero_base="/img/boats/mangusta-80/saloon",
        hero_widths=(600,900,1200),
        hero_alt="Corporate yacht charter Marbella — Mangusta 80 saloon set for client hosting",
        audience="Companies, agencies, incentive teams",
        breadcrumb_name="Corporate & Team Building",
    )


def render_honeymoon():
    body = '''<p>A honeymoon charter in Marbella is a different beast from a sunset cruise — usually 2 nights, not 2 hours. This page covers the actual playbook: which boat to book for an overnight, where we anchor for the night (rare in Spain — there are rules), how the catering works at anchor, and what makes the day-after morning unique.</p>

<figure class="inline-img"><img src="/img/boats/astondoa-40/interior-1200.jpg" srcset="/img/boats/astondoa-40/interior-600.jpg 600w, /img/boats/astondoa-40/interior-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Honeymoon yacht charter Marbella — cream-leather saloon on Astondoa 40" loading="lazy" width="1200" height="800"></figure>

<h2>Best boat for an overnight</h2>
<table>
<thead><tr><th>Couple style</th><th>Boat</th><th>Two-night package</th></tr></thead>
<tbody>
<tr><td>Intimate / classic Spanish</td><td><a href="/boats/astondoa-40/">Astondoa 40 "Fufi"</a></td><td>From €2,499 (boat + crew + overnight at marina + breakfast)</td></tr>
<tr><td>Modern flybridge</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>From €2,499</td></tr>
<tr><td>Luxury, jet ski included</td><td><a href="/boats/mangusta-80/">Mangusta 80 "Nina"</a></td><td>From €9,500 (skipper + deckhand crew, master suite, chef-grade galley)</td></tr>
</tbody>
</table>
<p>Day-only honeymoon (sunset + 4-hour charter): €1,299 starting on Astondoa or Azimut.</p>

<h2>Where you actually sleep</h2>
<p>Important to set expectations: Spanish maritime regulation prohibits overnight anchoring inside marina-controlled zones (Puerto Banús, Marbella Marina). For overnight stays, we either:</p>
<ul>
<li><strong>Stay at the marina berth</strong> at Puerto Banús — air-conditioned cabin, electricity, water hook-up, marina security, walking distance to dinner. Most popular and simplest.</li>
<li><strong>Anchor offshore at Río Verde or Cala del Faro</strong> — only in flat-sea forecasts (under 8-knot wind). Quieter, more romantic, but you'll feel the boat move. Permit zones are limited; we confirm 24h before.</li>
<li><strong>Move to a different marina for the night</strong> — Sotogrande or Estepona. Adds €200–€400 berth fee. The novel "second port" feel.</li>
</ul>

<h2>The two-night romantic itinerary</h2>
<p><strong>Day 1 — arrival</strong></p>
<ol>
<li><strong>16:00</strong> Check in at the boat, champagne in the saloon.</li>
<li><strong>17:00</strong> Sunset cruise to Río Verde. Anchor. Swim if warm enough.</li>
<li><strong>19:30</strong> Catered dinner on board (catering boats over from the dock) or short dinghy to a beach club.</li>
<li><strong>22:00</strong> Return to Puerto Banús for the night. Master cabin made up; air-con on.</li>
</ol>
<p><strong>Day 2 — full day</strong></p>
<ol>
<li><strong>09:00</strong> Breakfast on board (we cater fresh fruit, pastries, eggs, coffee). Eat in the cockpit.</li>
<li><strong>10:30</strong> Cast off. Cruise west to Estepona or east to Cabopino dunes. Two anchor stops for swim + snorkel.</li>
<li><strong>14:00</strong> Lunch at a beach restaurant (we tender you in). El Garum, Trocadero Sotogrande, Buddha Beach are easy.</li>
<li><strong>17:00</strong> Sunset slow cruise back to Puerto Banús. Optional dinner ashore — Casanis, La Sala, Sea Grill.</li>
</ol>
<p><strong>Day 3 — morning</strong></p>
<ol>
<li><strong>10:00</strong> Late check-out — breakfast on board if you want.</li>
<li><strong>11:00</strong> Crew handles the boat handover.</li>
</ol>

<h2>What we coordinate vs you book</h2>
<p><strong>We coordinate:</strong> the boat, skipper (and deckhand on Mangusta 80), fuel, drinks-on-board (cava, wine, beer), light snacks, anchor location selection, marina berth for the night, breakfast catering (€60/couple/morning).</p>
<p><strong>You arrange (we recommend):</strong> hotel for pre/post nights if needed, restaurant reservations ashore, your own special bottles, surprise gestures (flower bouquet, custom signage — let us know and we'll execute).</p>

<h2>Optional add-ons</h2>
<ul>
<li><strong>Catered dinner on board</strong> — €120/couple from local catering partners. Hot, multi-course, plated.</li>
<li><strong>Massage on the boat</strong> — €150 for a 60-min couples massage, therapist comes to the marina.</li>
<li><strong>Photographer for sunset shoot</strong> — €200/hour.</li>
<li><strong>Surprise rose-petal cabin setup</strong> — €80, we handle pre-arrival.</li>
<li><strong>Day-three Sotogrande lunch</strong> — extend by one day, lunch at a restaurant in the port. Quote on WhatsApp.</li>
</ul>

<h2>Pricing reality</h2>
<p>A two-night honeymoon on the Astondoa or Azimut, marina-stay (not anchored), with breakfast + one catered dinner, runs around <strong>€2,500–€3,200 all-in</strong>. The Mangusta 80 equivalent starts at €9,500 because of the larger crew and weekly-charter pricing logic. Day-only "luxury sunset" honeymoon for couples not staying overnight: €1,299 for 4 hours.</p>

<h2>Booking and timing</h2>
<p>Honeymoon bookings: 1–3 months ahead works for most dates; July–August Saturdays book 3–4 months ahead. Cancellation: full refund 14 days out, 50% inside 14 days, weather cancellations always 100%.</p>

<p>Tap <strong>Book now</strong> top-right with your wedding date and proposed honeymoon dates. We respond within 30 min with a specific itinerary built around your group, anchor preferences and dinner plans.</p>

<h2>Frequently asked questions</h2>
<details><summary>Can we anchor overnight away from any marina?</summary><p>Only in flat-sea forecasts and only at permitted anchorages (Río Verde, Cala del Faro). Spanish law restricts overnight anchoring near beaches and marinas. We confirm the night-before based on the weather forecast — most honeymoons end up at a marina berth, which is comfortable and air-conditioned.</p></details>
<details><summary>How does the bathroom situation work?</summary><p>Each cabin has its own marine head with shower. Hot water from the boat's heater. Toilet flushes to a holding tank emptied at the marina.</p></details>
<details><summary>Will we be alone on the boat?</summary><p>The skipper sleeps in the crew cabin (separate, forward) on multi-night charters. On the Astondoa or Azimut, you have the master cabin to yourselves; the skipper is on call but invisible. On the Mangusta 80, captain + deckhand have their own quarters and only appear at meals or when you request.</p></details>
<details><summary>What if we get seasick?</summary><p>Marina-overnight is virtually motionless. Anchored-offshore overnight you'll feel some rocking. We pick anchors carefully; if anyone is prone to seasickness we recommend the marina-stay option.</p></details>
<details><summary>Can we have dinner delivered to the boat?</summary><p>Yes — local catering partners deliver to the dock at Puerto Banús. We coordinate. €120/couple for a multi-course catered dinner.</p></details>'''
    render_tier1(
        slug="experiences/honeymoon-yacht-marbella",
        title="Honeymoon Yacht Charter Marbella: Two-Night Itineraries, Catered Dinners",
        meta="Honeymoon yacht charter Marbella — two-night package on Astondoa 40 or Azimut 39, catered dinners at anchor, breakfast on board, sunset cruises. From €2,499.",
        h1="Honeymoon Yacht Charter in Marbella",
        sub="Two nights on board, catered dinner at anchor, sunrise breakfast in the cockpit, Mediterranean anchor stops between Estepona and Cabopino.",
        eyebrow="Honeymoon · Marbella",
        body_html_str=body,
        hero_base="/img/boats/astondoa-40/interior",
        hero_widths=(600,900,1200),
        hero_alt="Honeymoon yacht charter Marbella — Astondoa 40 interior saloon",
        audience="Newlywed couples",
        breadcrumb_name="Honeymoon Charter",
    )


def render_snorkeling():
    body = '''<p>The Marbella coast has the clearest snorkeling water on the Costa del Sol — protected coves around Cabopino, deep clear water at Cala del Faro, sandy bottoms that hold visibility even on slightly windy days. This page is the snorkeling-specific playbook: which boat, which two anchor stops, what marine life you'll actually see, and gear logistics.</p>

<figure class="inline-img"><img src="/img/customers/h11-900.jpg" srcset="/img/customers/h11-400.jpg 400w, /img/customers/h11-600.jpg 600w, /img/customers/h11-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Snorkeling tour Marbella — guest at the bow of charter yacht" loading="lazy" width="1200" height="800"></figure>

<h2>The standard 4-hour snorkel tour</h2>
<ol>
<li><strong>10:30 — Boarding at Puerto Banús</strong>. Snorkel gear handed out at boarding (we have all sizes including junior). Quick water-clarity check from the skipper based on the morning forecast.</li>
<li><strong>11:00 — Cruise east 30 min</strong> to Cala Cortés (just past Cabopino marina). Sandy bottom, 3-5 m depth, sheltered from the levante.</li>
<li><strong>11:30 — Stop 1: Cala Cortés.</strong> 45 min in the water. Sea bream, small wrasse, occasional octopus, the odd ray on the sand.</li>
<li><strong>12:30 — Move 15 min east</strong> to Río Real anchorage. Mixed sand and rock.</li>
<li><strong>12:45 — Stop 2: Río Real.</strong> 45 min. Better fish density — bigger sea bream, schools of sand smelt, sometimes barracuda further out.</li>
<li><strong>13:45 — Snacks + cava back on board</strong>. Skipper sets the return route based on wind.</li>
<li><strong>14:30 — Return to Puerto Banús</strong>.</li>
</ol>
<p>4 hours, €1,299 on an Astondoa 40 or Azimut 39. Two snorkel sites, real fish, kids welcome.</p>

<h2>What you'll see in the water</h2>
<table>
<thead><tr><th>Species</th><th>How common</th><th>Where</th></tr></thead>
<tbody>
<tr><td>Sea bream (sargo)</td><td>Every stop</td><td>All anchorages, around rocks</td></tr>
<tr><td>Wrasse (señorita)</td><td>Every stop</td><td>Among rocks at Río Real, Cala del Faro</td></tr>
<tr><td>Sand smelt (chuleta)</td><td>Most stops</td><td>Open water in schools</td></tr>
<tr><td>Octopus (pulpo)</td><td>~30% of stops</td><td>Rock cracks at Río Real, Cala del Faro</td></tr>
<tr><td>Common stingray</td><td>~10% of stops</td><td>Sandy bottoms at Cala Cortés</td></tr>
<tr><td>Barracuda (small)</td><td>~10% of stops</td><td>Offshore-side of anchorages</td></tr>
<tr><td>Bluefin tuna passing</td><td>Rare, summer</td><td>Deep water 1-2 NM offshore</td></tr>
<tr><td>Dolphins (bonus)</td><td>~5% of trips</td><td>Cruise-by, not at anchor — see <a href="/blog/dolphin-watching-marbella/">dolphin tours</a></td></tr>
</tbody>
</table>

<h2>Best months for snorkeling</h2>
<p><strong>May–June and September–October</strong> are peak. Water 19-22 °C, visibility 6-10 m on calm days. <strong>July–August</strong> has warmer water (24 °C) and longer days but more boat traffic at the popular anchorages and afternoon levante stirs up the bottom. <strong>November–April</strong> water drops below 17 °C — possible with wetsuits (we don't provide, BYO) but most snorkelers stop in October.</p>

<h2>Gear we provide</h2>
<ul>
<li><strong>Adult snorkel masks + fins</strong> — multiple sizes, kept sanitised between charters.</li>
<li><strong>Junior masks + fins</strong> — for kids 6+, smaller silicone faces, junior-fit foot pockets.</li>
<li><strong>Snorkel vests / float belts</strong> for non-confident swimmers and kids.</li>
<li><strong>GoPro mounts</strong> for the swim platform if you bring your own camera.</li>
</ul>
<p>BYO if you have a prescription mask or want guaranteed fit. We don't provide wetsuits — bring or skip if water below 19 °C.</p>

<h2>Skipper tips that improve the day</h2>
<ul>
<li><strong>Enter the water from the swim platform</strong>, not by jumping — minimises disturbance to the fish.</li>
<li><strong>Stay 10 m from the boat</strong> if there's any wind drift. Skipper watches but it gets tiring to fight the current back.</li>
<li><strong>No feeding the fish</strong> — illegal in Spanish waters, plus it changes their behaviour for weeks.</li>
<li><strong>Look down, not at the surface</strong> — sounds obvious but most first-time snorkelers spend half the dip staring at their fins.</li>
<li><strong>Watch the rocks at Río Real</strong> — that's where octopuses hide. Quick scan of cracks at 2-3 m depth usually finds one.</li>
</ul>

<h2>Safety basics</h2>
<ul>
<li>Skipper stays on board with the engine off, watching the water at all times.</li>
<li>Snorkel area is marked with a flag on the swim platform — boats keep distance.</li>
<li>Kids must wear snorkel vests at all times in the water.</li>
<li>Sea-urchin awareness at rocky entries — Cala Cortés is sandy and safer for kids.</li>
</ul>

<h2>Booking</h2>
<p>Tap <strong>Book now</strong> top-right. Tell us your date, group size (including kids' ages), and any snorkel experience level. We pick the best two anchorages for that day's wind and mark the gear sizes you'll need.</p>

<h2>Frequently asked questions</h2>
<details><summary>Do I need to know how to swim?</summary><p>Yes — you should be a comfortable swimmer for the snorkel tour. Non-swimmers can stay on the boat and watch through the glass swim platform, or use a flotation belt to stay at the surface near the boat.</p></details>
<details><summary>What ages can snorkel?</summary><p>From age 6, with a junior mask and snorkel vest. Younger kids stay on board with a parent. Older kids (10+) are great snorkelers on the Marbella coast — clear water, easy depths.</p></details>
<details><summary>What if there's no marine life that day?</summary><p>We move to a second stop if the first is unproductive. In 4 hours, you almost always see sea bream and wrasse. Octopus is the lucky find. We don't refund "no fish" — it's wildlife, but we work hard to find them.</p></details>
<details><summary>Can I bring my own underwater camera / GoPro?</summary><p>Yes — and we'll mount it on the swim platform or bow if you want a stationary shot of you snorkeling. No drone fishing or spear-fishing (we strictly don't run those — protected coast).</p></details>
<details><summary>What if it's too windy?</summary><p>If forecast wind exceeds Force 4 the visibility drops below 3 m and snorkeling isn't worth it. The skipper calls the night before — we reschedule or refund 100%.</p></details>'''
    render_tier1(
        slug="experiences/snorkeling-tour-marbella",
        title="Snorkeling Tour Marbella: Two Anchorages, Real Marine Life",
        meta="Marbella snorkeling tour from €1,299 / 4h — anchored at Cala Cortés + Río Real for clear-water snorkel stops. Sea bream, wrasse, octopus. Junior masks + flotation provided.",
        h1="Snorkeling Tour in Marbella",
        sub="Two anchor stops at the clearest spots between Cabopino and Cala del Faro — gear in all sizes, kids welcome, sea bream and the lucky octopus.",
        eyebrow="Snorkeling · Marbella",
        body_html_str=body,
        hero_base="/img/customers/h11",
        hero_widths=(400,600,900),
        hero_alt="Snorkeling tour Marbella — charter yacht at anchor at Río Real",
        audience="Families, snorkel-curious travellers, marine life enthusiasts",
        breadcrumb_name="Snorkeling Tour",
    )


def render_birthday():
    body = '''<p>A birthday on a yacht in Marbella is one of the easiest "yes-I'll-come" group invites you can send. Half-day from €1,299, BYO cava welcomed, the boat handles the entertainment for you. This page covers the practical bits: which boat for which age, the standard 4-hour script, what we pre-load if you ask, and how to coordinate the cake without it melting in 32 °C heat.</p>

<figure class="inline-img"><img src="/img/customers/h14-900.jpg" srcset="/img/customers/h14-400.jpg 400w, /img/customers/h14-600.jpg 600w, /img/customers/h14-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Birthday yacht charter Marbella — group of friends celebrating on the bow" loading="lazy" width="1200" height="800"></figure>

<h2>Best boat for the birthday</h2>
<table>
<thead><tr><th>Birthday type</th><th>Boat</th><th>Half-day</th></tr></thead>
<tbody>
<tr><td>Couple's birthday (intimate)</td><td><a href="/sunset-cruise-marbella/">Sunset cruise</a> on the Astondoa 40</td><td>€749 / 2 h</td></tr>
<tr><td>Friends weekend, 6–8 guests</td><td><a href="/boats/astondoa-40/">Astondoa 40 "Fufi"</a></td><td>€1,299 / 4 h</td></tr>
<tr><td>Bigger group, 9–11 guests</td><td><a href="/boats/azimut-39/">Azimut 39</a></td><td>€1,299 / 4 h</td></tr>
<tr><td>Milestone (30th, 40th, 50th) with full luxury</td><td><a href="/boats/mangusta-80/">Mangusta 80 "Nina"</a></td><td>€4,719 / 4 h, jet ski included</td></tr>
<tr><td>Kids' birthday (8–14 yo)</td><td><a href="/experiences/family-boat-days-marbella/">Family-day style</a> on Astondoa</td><td>€1,299 / 4 h</td></tr>
</tbody>
</table>

<h2>The standard 4-hour birthday script</h2>
<ol>
<li><strong>14:00 — Boarding at Puerto Banús</strong>. Cava already chilling. Birthday banners pre-rigged if you sent us decorations the morning of.</li>
<li><strong>14:30 — Cast off</strong>. Slow cruise west along the Golden Mile, music playing, group settling in.</li>
<li><strong>15:15 — Anchor at Río Verde</strong>. Swim, donut, paddleboard. Music up. This is where the day actually starts.</li>
<li><strong>16:00 — Birthday photo set</strong>. Skipper repositions for the group shot with La Concha behind. Photographer (if booked) works the group.</li>
<li><strong>16:45 — Cake moment</strong>. We bring the cake out from the galley fridge (we store it from boarding). Candles, song, photo. Slice and serve.</li>
<li><strong>17:30 — Return cruise</strong> to Puerto Banús, slower the second half, music down, golden-hour light on the coast.</li>
<li><strong>18:00 — Disembark</strong>. Taxis or walk to dinner.</li>
</ol>

<h2>The cake situation</h2>
<p>Marbella summer is hot. A cake left on a sun-pad for 30 minutes is a disaster. What works:</p>
<ul>
<li><strong>Buttercream-style fondant cakes</strong> hold up best — refrigerate on board until the moment.</li>
<li><strong>Cream-based cakes</strong> melt fast — keep refrigerated until the cake moment, serve immediately.</li>
<li><strong>Ice-cream cakes</strong> need the freezer (we have one) — call 24 h ahead and we'll prep the freezer space.</li>
<li><strong>Bring the cake at boarding</strong> in a cool box if you can. We transfer it straight to the fridge.</li>
</ul>
<p>Marbella bakeries that deliver to Puerto Banús dock and that we've worked with happily: La Tahona (classic Spanish), Sweet Boutique (custom), El Horno de Tata (English-style sponge). Tell them the boat name and arrival time.</p>

<h2>What we pre-load on request (24 h notice)</h2>
<ul>
<li>Extra cava beyond what's already included (the boat has 4 bottles included; for 11 guests assume 6-8 total).</li>
<li>Birthday banners on the bow (you supply, we hang).</li>
<li>"Happy Birthday" balloons floating on the swim platform.</li>
<li>Bottles of specific spirits you've BYO'd.</li>
<li>Catered platters (€25-80/head, see below).</li>
</ul>

<h2>Catering add-ons</h2>
<ul>
<li><strong>Tapas board</strong> (jamón, queso manchego, olives, breadsticks) — €25/head</li>
<li><strong>Sushi platter</strong> from a local sushi-master — €35/head</li>
<li><strong>Paella party</strong> (hot, served from the galley) — €55/head</li>
<li><strong>Full hot lunch</strong> (Spanish or Mediterranean, multi-course) — €60-80/head</li>
</ul>
<p>All catering arrives at the dock 30 min before departure. We coordinate.</p>

<h2>Music + DJ</h2>
<p>Bluetooth speakers on board, you bring your playlist. For "real party" energy, add a pro DJ + speaker upgrade — €350 for the half-day. Or hire a saxophonist who plays from the bow (€400–€600) — it's the most Marbella thing you can do.</p>

<h2>Best months for a birthday charter</h2>
<p>Mid-June to mid-September is peak — warm sea, long days, beach club scene at full volume. Most popular weekend month: July. <strong>September weekdays</strong> are the secret-good slot: same boat, same weather, 10–15% off, way easier availability. October is still warm enough to swim and the Saturday is much quieter. Outside that window we run charters but it's bring-a-jacket weather.</p>

<h2>Booking</h2>
<p>Tap <strong>Book now</strong> top-right. Tell us the birthday date, group size, age (so we match the right boat and music vibe), and any specific add-ons (cake delivery, DJ, photographer). We respond within 5 min on WhatsApp with 2-3 specific boat options + the itemised quote.</p>

<h2>Frequently asked questions</h2>
<details><summary>Can we bring our own cake?</summary><p>Yes — bring at boarding in a cool box. We transfer to the fridge until the cake moment. Or order delivery from a Marbella bakery to the Puerto Banús dock — we coordinate.</p></details>
<details><summary>Can we bring our own alcohol?</summary><p>Yes on private charters. Cava, beer and white wine are already on board. BYO spirits / mixers / extra bubbly is welcomed. Cans and plastic only on deck — no glass.</p></details>
<details><summary>Can we have decorations?</summary><p>Yes — banners, balloons, signs, photo props. Bring them at boarding; we rig them. No confetti, glitter, or anything that goes overboard.</p></details>
<details><summary>What's the minimum age for kids' birthdays?</summary><p>No minimum on our boats but for under-8s we recommend a family-day style itinerary (calmer water, shorter swim stops). See <a href="/experiences/family-boat-days-marbella/">family boat days</a>.</p></details>
<details><summary>Can we extend the charter if everyone's having fun?</summary><p>Often yes, if the boat isn't booked for a subsequent slot. Extra hours cost 80-100% of the hourly rate, paid before extending. Tell the skipper at hour 3 and they'll check.</p></details>'''
    render_tier1(
        slug="experiences/birthday-yacht-marbella",
        title="Birthday Yacht Charter Marbella: 4-Hour Script, Cake Logistics",
        meta="Birthday yacht charter Marbella from €1,299 / 4 h on our 12.5 m fleet, or €4,719 on the Mangusta 80 superyacht. Cake handled, BYO welcomed, photographer on request.",
        h1="Birthday on a Yacht in Marbella",
        sub="Cava at noon, anchor swim, the cake moment — your group, your music, our crew handling everything else.",
        eyebrow="Birthday · Marbella",
        body_html_str=body,
        hero_base="/img/customers/h14",
        hero_widths=(400,600,900),
        hero_alt="Birthday yacht charter Marbella — group celebrating on the bow",
        audience="Birthday celebrants and their groups",
        breadcrumb_name="Birthday on a Yacht",
    )


def render_proposal():
    body = '''<p>The most-asked question we get from couples: "Can you help me propose on the boat?" Yes. We've done it a hundred times — and the skipper-coordinated script below is the playbook that actually works (vs the panicked-bag-of-Ring-Boxes approach). 2-hour sunset cruise, anchor stop at Río Verde, cava ready, ring hidden until the moment. €749 + a few small extras.</p>

<figure class="inline-img"><img src="/img/customers/h04-1200.jpg" srcset="/img/customers/h04-600.jpg 600w, /img/customers/h04-900.jpg 900w" sizes="(max-width: 880px) 100vw, 720px" alt="Proposal on a yacht in Marbella — partner at the bow at sunset" loading="lazy" width="1200" height="800"></figure>

<h2>How the skipper-coordinated proposal works</h2>
<p>You enquire by WhatsApp, we set up a quick voice call (skipper-to-proposer, 5 min) to coordinate:</p>
<ol>
<li><strong>What does the partner know?</strong> Surprise sunset cruise, or surprise proposal-on-the-cruise? Affects how the day unfolds.</li>
<li><strong>The ring.</strong> Bring it onboard hidden however you want — we'll secure it in the galley fridge / saloon drawer / skipper-pocket. Don't have it visible in carry-on at boarding.</li>
<li><strong>The moment.</strong> Default: anchor at Río Verde with La Concha behind, just before the sun touches the horizon. Cava poured. You step to the bow. We discreetly disappear.</li>
<li><strong>The signal.</strong> You tell us the signal before — usually "when I move to the bow, bring the cava and step back". The skipper has the discretion of someone who has done this a hundred times.</li>
<li><strong>The aftermath.</strong> Champagne pop. Photo set the skipper takes from the helm (your phone, or your photographer's phone if you've hired one). Cruise back to Puerto Banús with the music on.</li>
</ol>

<h2>The 2-hour proposal cruise — hour by hour</h2>
<ol>
<li><strong>T-75 min before sunset — Boarding</strong> at Puerto Banús. Welcome drink at the dock (chilled cava). Skipper briefs you both on safety, you brief skipper privately on the signal.</li>
<li><strong>T-60 min — Cast off</strong>. Slow cruise west past Marbella Club and Puente Romano. The Golden Mile mansions are the warm-up.</li>
<li><strong>T-30 min — Anchor at Río Verde</strong>. Calm water. La Concha behind. Music down low. Skipper hands you both a glass.</li>
<li><strong>T-15 min — You step to the bow.</strong> Or wait for the signal you'd agreed. Skipper gets out of the frame.</li>
<li><strong>T-0 — The moment.</strong> Cava pop. The skipper takes the photo from the helm (with your camera or partner's).</li>
<li><strong>T+15 min — Cruise return</strong> at displacement speed. Sunset light, music on, you've got 30 minutes to call your families.</li>
<li><strong>T+45 min — Back at Puerto Banús.</strong> Photo on the dock. Dinner reservation we held for you at Casanis or La Sala.</li>
</ol>

<h2>Add-ons couples ask for</h2>
<ul>
<li><strong>Photographer on board</strong> — €200/h, captures the moment from the helm (you don't notice them; skipper signals them).</li>
<li><strong>Videographer / reel</strong> — €300/h, edit delivered 48 h later.</li>
<li><strong>Flowers on the bow</strong> — €60-€120, white roses or your choice. Pre-set before boarding.</li>
<li><strong>Custom cava bottle</strong> — your label, "Will you marry me?" engraving. Local Marbella shop, we coordinate. €120.</li>
<li><strong>Restaurant booking ashore</strong> — we hold a 2-top reservation at Casanis, La Sala, Sea Grill or Skina (your choice). Confirms after the yes.</li>
<li><strong>Acoustic musician on board</strong> — Spanish guitar at sunset. €400.</li>
</ul>

<h2>The classic Río Verde sunset shot</h2>
<p>The proposal photo every couple wants is: you (proposing) on the bow at the centre, partner looking back at you, La Concha mountain behind, sun touching the horizon to camera-right, water reflecting orange. The skipper knows the angle. We anchor with the boat oriented for it. If you've hired a photographer, they get the wide and the close, plus the candid afterwards. If not, the skipper takes a few from the helm — they're not Annie Leibovitz but they're solid.</p>

<h2>Best months for a proposal</h2>
<p><strong>May, June, September</strong> are the sweet spot — sunset 20:30–21:00, water 19-22 °C, levante winds gentler than peak summer. <strong>July–August</strong> works but sunset is later (21:30+) and the Río Verde anchorage is busier. <strong>October</strong> sunsets are early (19:45) but the light is the warmest. Winter proposals happen but it's cold for outdoor cava.</p>

<h2>What we don't do</h2>
<ul>
<li>Pre-printed signs that ruin the spontaneity (unless you specifically request).</li>
<li>Drones flying over the boat at the moment (Spanish law restricts this; also kills the privacy).</li>
<li>Fake "engine breakdown" so you have to step on deck (it's been pitched; we don't).</li>
<li>Tell the partner anything before — we hold every secret.</li>
</ul>

<h2>Pricing</h2>
<p>Base: €749 for the 2-hour sunset cruise. Add photographer (€200), custom flowers (€80), restaurant booking (free coordination, you pay at the restaurant). Most proposal couples spend around €900-€1,200 all-in including dinner ashore.</p>

<h2>Booking</h2>
<p>Tap <strong>Book now</strong> top-right with the date, the partner's name (so we don't accidentally call them by the wrong name when greeting), and your signal preference. We respond within 5 minutes on WhatsApp. Then a 5-minute call to coordinate. Then we disappear until you message us with "she said yes" so we can pop the second bottle.</p>

<h2>Frequently asked questions</h2>
<details><summary>What if the partner figures it out before the moment?</summary><p>Happens about 20% of the time, especially if they notice flowers or extra cava. Doesn't ruin the moment — usually makes it warmer. We don't overplay the "act surprised" angle; you're both adults.</p></details>
<details><summary>Can the skipper hide the ring?</summary><p>Yes — we routinely hold the ring in a galley drawer or the skipper's pocket. Hand it over at boarding privately. The skipper hands it back at your agreed signal.</p></details>
<details><summary>What if they say no?</summary><p>Statistically rare on a sunset-cruise proposal in Marbella but it happens. The skipper handles it gracefully — slow cruise back, music down, no pressure. We've been there. The €749 is non-refundable but we don't charge for the second bottle.</p></details>
<details><summary>Can we do the proposal mid-day instead of sunset?</summary><p>Yes — though sunset is dramatically better for the photo. Mid-day with the snorkel stop also works ("I have a question to ask you between dips"). Pick what fits the partner.</p></details>
<details><summary>Can we have family on a second boat watching?</summary><p>Yes — we synchronise two boats anchoring 100 m apart. The "surprise family appearance" version. Quote separately.</p></details>'''
    render_tier1(
        slug="experiences/proposal-yacht-marbella",
        title="Proposal on a Yacht in Marbella: Captain's Playbook (Sunset Cava + La Concha)",
        meta="How to propose on a yacht in Marbella — skipper-coordinated 2-hour sunset cruise at Río Verde, cava ready, ring hidden, photographer optional. From €749.",
        h1="Proposal on a Yacht in Marbella",
        sub="The skipper-coordinated playbook — sunset cava at Río Verde, La Concha behind, the photo you've imagined in your head for months.",
        eyebrow="Proposal · Marbella",
        body_html_str=body,
        hero_base="/img/customers/h04",
        hero_widths=(400,600,900),
        hero_alt="Proposal on a yacht in Marbella — partner at the bow at sunset",
        audience="Couples planning a proposal",
        breadcrumb_name="Proposal on a Yacht",
    )


def render_anniversary():
    body = '''<p>An anniversary yacht charter is the opposite of a stag party. Half-day for two, quiet music, anchor stop with cava, dinner ashore at a place you've been wanting to try. This page covers the standard "for two" itinerary, what's different from a sunset cruise, and the practical upsells couples ask for (catered dinner on board, photographer, restaurant booking).</p>

<figure class="inline-img"><img src="/img/boats/astondoa-40/sunset-1200.jpg" srcset="/img/boats/astondoa-40/sunset-600.jpg 600w, /img/boats/astondoa-40/sunset-900.jpg 900w, /img/boats/astondoa-40/sunset-1200.jpg 1200w" sizes="(max-width: 880px) 100vw, 720px" alt="Anniversary yacht charter Marbella — Astondoa 40 at Puerto Banús sunset" loading="lazy" width="1200" height="800"></figure>

<h2>Anniversary vs sunset cruise — what's different</h2>
<p>Sunset cruise (€749 / 2 h) and anniversary cruise are the same product on paper, but couples want a different feel:</p>
<ul>
<li><strong>Longer at anchor</strong> — 4 h half-day rather than 2 h cruise. Time to actually relax, not just cross the bay.</li>
<li><strong>Lunch on board</strong> — anchored, catered. Not a 30-min drink stop.</li>
<li><strong>One boat, one couple</strong> — bigger boat than you need (more space for two on a 12.5 m yacht than a sport boat), more privacy.</li>
<li><strong>Sometimes overnight</strong> — see also our <a href="/experiences/honeymoon-yacht-marbella/">honeymoon charter</a>.</li>
</ul>

<h2>Best boat for two</h2>
<table>
<thead><tr><th>Style</th><th>Boat</th><th>4-h half-day</th></tr></thead>
<tbody>
<tr><td>Classic Mediterranean</td><td><a href="/boats/astondoa-40/">Astondoa 40 "Fufi"</a> — teak interior, twin-cabin for siesta</td><td>€1,299</td></tr>
<tr><td>Modern flybridge</td><td><a href="/boats/azimut-39/">Azimut 39</a> — flybridge sunpad upstairs, AC saloon downstairs</td><td>€1,299</td></tr>
<tr><td>Pure luxury (special anniversaries — 10th, 25th)</td><td><a href="/boats/mangusta-80/">Mangusta 80 "Nina"</a> — three cabins, marble galley, jet ski included</td><td>€4,719</td></tr>
</tbody>
</table>

<h2>The standard "anniversary for two" half-day</h2>
<ol>
<li><strong>15:00 — Boarding at Puerto Banús</strong>. Welcome cava in the cockpit. Skipper briefs in 90 seconds and gets out of your way.</li>
<li><strong>15:30 — Cast off</strong>. Slow cruise west past the Golden Mile.</li>
<li><strong>16:15 — Anchor at Cala del Faro</strong> (further than the standard sunset cruise — about 25 NM west). Quieter than Río Verde, deeper water, cleaner snorkel.</li>
<li><strong>16:30 — Catered lunch on board.</strong> We coordinate with a local catering partner — set up on the cockpit table, plated. Multi-course Mediterranean for two: €120-180/couple.</li>
<li><strong>17:30 — Swim, paddleboard, nap.</strong> Master cabin available for an actual siesta.</li>
<li><strong>18:30 — Slow cruise back</strong> as the sun starts dropping behind Gibraltar (on clear days).</li>
<li><strong>19:00 — Disembark at Puerto Banús.</strong> Optional dinner reservation we hold for you at Casanis, La Sala or Sea Grill.</li>
</ol>

<h2>Optional add-ons for anniversaries</h2>
<ul>
<li><strong>Catered multi-course lunch on board</strong> — €120-180 for two, served at anchor. Local catering partner.</li>
<li><strong>Photographer for the day</strong> — €200/h, captures candid and posed. Album delivered 48 h later.</li>
<li><strong>Custom cava with your label</strong> — €120, anniversary year engraved. Pre-loaded.</li>
<li><strong>Flowers on the swim platform</strong> — €60–€120, roses floating for the surprise reveal.</li>
<li><strong>Couples massage at the dock</strong> — book the marina-side spa treatment for after the charter. We coordinate timing.</li>
<li><strong>Restaurant booking ashore</strong> — we hold a 2-top reservation at any Marbella restaurant. Confirm in advance.</li>
<li><strong>Spanish guitarist on board</strong> — acoustic, romantic, €400.</li>
</ul>

<h2>Milestone anniversaries — go bigger</h2>
<p>For 10th / 25th / 50th anniversaries, couples often upgrade to the Mangusta 80 — the chef-grade galley supports a proper catered dinner at anchor, the master suite makes it possible to stay overnight, the jet ski is included for the fun-younger version of yourselves. €4,719 base + catering + photographer = €5,500-€6,500 for a milestone day. Includes a sunrise breakfast onboard the next morning if you stay overnight.</p>

<h2>Surprise anniversary — secret coordination</h2>
<p>If you're surprising your partner, message us privately first. We handle:</p>
<ul>
<li>Booking under a different name if your partner shares your WhatsApp.</li>
<li>Hold the boat without communication going to your home email.</li>
<li>Coordinate the surprise reveal (e.g. "we're going to lunch", then they realise it's a yacht).</li>
<li>Pre-load gifts onto the boat (flowers, jewellery box, framed photo, etc).</li>
</ul>

<h2>Best months for anniversaries</h2>
<p>Same as proposal cruises — <strong>May, June, September</strong> are the sweet spot. <strong>October</strong> is quietly excellent for shoulder-season anniversaries (warm light, quieter coast, 10-15% lower rates). For anniversaries on specific calendar dates, book 3-4 weeks ahead in peak season, 1 week ahead off-peak.</p>

<h2>Booking</h2>
<p>Tap <strong>Book now</strong> top-right with the anniversary date, surprise vs joint planning, any specific add-ons (catered lunch, photographer, restaurant booking), and which boat appeals. We respond within 5 minutes on WhatsApp with a tailored proposal.</p>

<h2>Frequently asked questions</h2>
<details><summary>How is this different from a sunset cruise?</summary><p>Sunset cruise is 2 h focused on the sunset itself. Anniversary half-day is 4 h with a catered lunch at anchor, more relaxation, longer in one spot, often dinner ashore after. More money but a much more substantial day.</p></details>
<details><summary>Can we have privacy on the boat?</summary><p>Yes — the skipper stays at the helm during cruising; at anchor they retreat below deck and only appear when you call. On the Mangusta 80 with two crew, they have their own quarters and are deliberately invisible.</p></details>
<details><summary>What's the best month for our anniversary?</summary><p>May, June, September, October. Avoid Saturday in August (busy + expensive). Weekdays in May or October give you the calmest sea + lowest prices.</p></details>
<details><summary>Can we book the boat for just dinner — not a cruise?</summary><p>Yes — a 2-hour dinner-at-marina booking (boat stays at the berth, you eat onboard at the cockpit table) is bookable for around €499. Includes the boat, drinks, light snacks. Catering you'd order separately.</p></details>
<details><summary>Can we stay overnight after the anniversary day?</summary><p>Yes — extend to an overnight + breakfast for an additional €1,200–€1,800 depending on boat. Marina-stay at Puerto Banús, master cabin made up, breakfast catered the next morning.</p></details>'''
    render_tier1(
        slug="experiences/anniversary-yacht-marbella",
        title="Anniversary Yacht Charter Marbella: Half-Day for Two, Sunset Anchor",
        meta="Anniversary yacht charter Marbella from €1,299 / 4 h — catered lunch at anchor at Cala del Faro, sunset return, restaurant booking ashore. Astondoa 40, Azimut 39, or Mangusta 80.",
        h1="Anniversary Yacht Charter in Marbella",
        sub="A quiet half-day for two — anchor at Cala del Faro, catered lunch on the cockpit table, sunset cruise home.",
        eyebrow="Anniversary · Marbella",
        body_html_str=body,
        hero_base="/img/boats/astondoa-40/sunset",
        hero_widths=(600,900,1200,1600),
        hero_alt="Anniversary yacht charter Marbella — Astondoa 40 at Puerto Banús sunset",
        audience="Couples celebrating an anniversary",
        breadcrumb_name="Anniversary Cruise",
    )


def main():
    render_hub()
    render_family()
    render_photoshoot()
    render_bachelor_hen()
    # Tier-1 batch
    render_wedding()
    render_corporate()
    render_honeymoon()
    render_snorkeling()
    render_birthday()
    render_proposal()
    render_anniversary()

if __name__ == "__main__":
    main()
