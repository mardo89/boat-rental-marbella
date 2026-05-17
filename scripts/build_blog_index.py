#!/usr/bin/env python3
"""Generate /blog/index.html — a card-grid listing of every blog post.

Reads content/blog_*.json (built by generate_pages.py), produces an aggregation
page rendered through templates/page.html.template so it matches the rest of
the site (header, hero overlay, sidebar book-card, footer).

Run after content changes:
    python3 scripts/build_blog_index.py
"""
from __future__ import annotations
import json, pathlib, html, re
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SITE_DIR = ROOT / "site"
TEMPLATE = (ROOT / "templates" / "page.html.template").read_text()
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
SITE = CONFIG["site"]

INDEX_HERO_IMG = "https://images.pexels.com/photos/15488149/pexels-photo-15488149.jpeg?auto=compress&cs=tinysrgb&w=1600"
INDEX_HERO_ALT = "Aerial view of Marbella's coastline — the Marbella charter guide"
INDEX_TITLE = "Marbella Boat Charter Guide: Prices, Routes, Rules & Tips"
INDEX_META = "The complete 2026 guide to chartering a boat in Marbella — prices, license rules, best months, kids on board, Gibraltar by sea, seasickness prevention and more."
INDEX_H1 = "The Marbella Boat Charter Guide"
INDEX_SUB = "Practical, captain-tested answers to every question about renting a boat in Marbella — written for first-timers and seasoned charterers alike."

def pexels(src, w):
    return re.sub(r'[?&]w=\d+', '', src).rstrip('?&') + ('&' if '?' in src else '?') + f"w={w}"

def load_blog_posts():
    posts = []
    for f in sorted(CONTENT.glob("blog_*.json")):
        d = json.loads(f.read_text())
        p = d["page"]; data = d["data"]
        posts.append({
            "slug": "/" + p["slug"] + "/",
            "title": p["title"],
            "primary_keyword": p["primary_keyword"],
            "summary": data.get("summary","") or data.get("meta_description",""),
            "hero": data.get("hero_img"),
            "hero_alt": data.get("hero_alt", p["primary_keyword"]),
        })
    return posts

def render_post_card(post):
    src = post["hero"] or "https://picsum.photos/seed/" + post["slug"].strip("/") + "/600/375"
    srcset = ", ".join(f"{pexels(src, w)} {w}w" for w in (400, 600, 900))
    return f'''<a href="{post["slug"]}" class="boat-card">
  <div class="boat-card-img">
    <img src="{pexels(src, 600)}" srcset="{srcset}" sizes="(max-width: 600px) 100vw, 360px" alt="{html.escape(post["hero_alt"])}" loading="lazy" width="600" height="375">
  </div>
  <div class="boat-card-body">
    <h3 class="boat-card-title">{html.escape(post["title"])}</h3>
    <p class="boat-card-desc">{html.escape(post["summary"])}</p>
    <div class="boat-card-meta">
      <span class="boat-card-price" style="font-size:.9rem;font-weight:600;color:var(--c-muted)">Guide</span>
      <span class="boat-card-cta">Read →</span>
    </div>
  </div>
</a>'''

def main():
    posts = load_blog_posts()
    cards = "\n".join(render_post_card(p) for p in posts)

    body = f'''<p class="byline">{len(posts)} guides · Updated {date.today().strftime("%-d %B %Y")} · Reviewed by local Marbella skippers</p>

<p>Everything we'd tell a friend who'd just booked a flight to Málaga and asked "should we charter a boat?" — broken into focused guides you can read in 5 minutes each. Prices in 2026 €, rules for Spanish waters, weather windows, and the small things that make the difference between a great day and a forgettable one.</p>

<section class="boat-grid-section" style="background:transparent;padding:24px 0 0">
  <div class="boat-grid" style="padding:0">
{cards}
  </div>
</section>

<h2>Browse by intent</h2>
<ul>
  <li><strong>Planning a trip:</strong> <a href="/blog/best-month-to-rent-a-boat-in-marbella/">best month</a>, <a href="/blog/how-much-does-it-cost-to-rent-a-boat-in-marbella/">how much it costs</a>, <a href="/blog/puerto-banus-vs-marbella-marina/">which marina to use</a>.</li>
  <li><strong>Rules &amp; logistics:</strong> <a href="/blog/boat-license-rules-spain/">Spain license rules</a>, <a href="/blog/what-to-bring-on-a-boat-charter/">packing checklist</a>, <a href="/blog/private-vs-shared-boat-charter/">private vs shared</a>.</li>
  <li><strong>On the water:</strong> <a href="/blog/kids-on-a-boat-marbella/">with kids</a>, <a href="/blog/seasickness-prevention-charter/">avoiding seasickness</a>, <a href="/blog/dolphin-watching-marbella/">dolphin watching</a>, <a href="/blog/gibraltar-day-trip-by-boat/">Gibraltar by boat</a>.</li>
</ul>

<p>Ready to book? Compare every boat type and message us on WhatsApp from the <a href="/">boat rental Marbella</a> hub.</p>
'''

    # Build JSON-LD: ItemList of posts + BreadcrumbList + Organization
    jsonld = [
        {
            "@context":"https://schema.org","@type":["LocalBusiness","Organization"],
            "@id": SITE['base_url']+"/#org","name":SITE['name'],
            "url":SITE['base_url']+"/","logo":SITE['base_url']+"/og-image.jpg",
            "telephone":SITE['phone_e164'],"email":SITE['email'],
            "areaServed":SITE['departure_ports'],
            "sameAs":[u for u in [SITE.get('instagram_url'), SITE.get('facebook_url')] if u],
            "priceRange":f"€{SITE['price_anchor_low_2h']}–€{SITE['price_anchor_fullday_8h']}",
            "address":{"@type":"PostalAddress","addressLocality":"Marbella","addressRegion":"Andalucía","postalCode":"29602","addressCountry":"ES"},
            "geo":{"@type":"GeoCoordinates","latitude":SITE['geo_lat'],"longitude":SITE['geo_lng']},
            "foundingDate": str(SITE.get('founded_year',2025)),
        },
        {
            "@context":"https://schema.org","@type":"CollectionPage",
            "name": INDEX_TITLE,"url": SITE['base_url']+"/blog/",
            "description": INDEX_META,
            "isPartOf":{"@id":SITE['base_url']+"/#org"},
            "mainEntity":{
                "@type":"ItemList",
                "numberOfItems": len(posts),
                "itemListElement":[
                    {"@type":"ListItem","position":i+1,
                     "url": SITE['base_url']+p["slug"],
                     "name": p["title"]}
                    for i, p in enumerate(posts)
                ],
            },
        },
        {
            "@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":SITE['base_url']+"/"},
                {"@type":"ListItem","position":2,"name":"Guide","item":SITE['base_url']+"/blog/"},
            ],
        },
    ]

    # Hero srcset
    hero_srcset = ", ".join(f"{pexels(INDEX_HERO_IMG, w)} {w}w" for w in (640, 960, 1280, 1600))

    repl = {
        "{{HERO_IMG}}": INDEX_HERO_IMG,
        "{{HERO_SRCSET}}": html.escape(hero_srcset),
        "{{HERO_ALT}}": html.escape(INDEX_HERO_ALT),
        "{{HERO_EYEBROW}}": '<span class="eyebrow">Guides · Marbella</span>',
        "{{HERO_H1}}": html.escape(INDEX_H1),
        "{{HERO_SUB}}": html.escape(INDEX_SUB),
        "{{TITLE}}": html.escape(INDEX_TITLE),
        "{{META_DESCRIPTION}}": html.escape(INDEX_META),
        "{{CANONICAL_URL}}": SITE['base_url']+"/blog/",
        "{{OG_TYPE}}": "website",
        "{{CSS_HREF}}": "/styles.css",
        "{{JSONLD}}": json.dumps(jsonld, ensure_ascii=False),
        "{{PRICE_LOW}}": str(SITE['price_anchor_low_2h']),
        "{{BOAT_GRID}}": "",
        "{{BREADCRUMBS}}": '<nav class="breadcrumbs"><a href="/">Home</a> › <span>Guide</span></nav>',
        "{{BODY_HTML}}": body,
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

    out_path = SITE_DIR / "blog" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)
    print(f"blog index: {len(posts)} posts → {out_path}")

if __name__ == "__main__":
    main()
