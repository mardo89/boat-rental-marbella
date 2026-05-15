# Boat Rental Marbella — affiliate SEO site

Static HTML site targeting "boat rental Marbella" and related keywords. Affiliate lead-gen model (WhatsApp + Click&Boat fallback). Built in this worktree following [the approved plan](../../.claude/plans/boat-rental-marbella-website-vast-lovelace.md).

## Status (2026-05-16)

- **Competitor:** [marbellaboatcharter.com](https://marbellaboatcharter.com/) (#1 organic). Notes in `config/competitor_analysis.md`.
- **Pages live (6/19):** hub, yacht-charter-marbella, catamaran-rental-marbella, boat-rental-no-license-marbella, blog/how-much-does-it-cost-to-rent-a-boat-in-marbella, blog/boat-license-rules-spain.
- **Pages pending (13/19):** fishing-boat-rental-marbella, boat-rental-puerto-banus, sunset-cruise-marbella, boat-party-marbella, luxury-yacht-rental-marbella, plus 8 more blog posts.
- **Reason 13 pages are pending:** the Anthropic API key in `/Users/mardosoo/aiangels-blog/.env` returned `credit balance is too low` — top up at https://console.anthropic.com/settings/billing then run the generator (see below).

## Layout

```
seo_sites/boat_rental_marbella/
├── README.md
├── config/
│   ├── keyword_map.json          # site facts + 19 page configs
│   └── competitor_analysis.md
├── templates/
│   └── page.html.template        # single template for all pages
├── scripts/
│   ├── generate_pages.py         # Claude API → content/<slug>.json + site/<slug>/index.html
│   ├── build_link_graph.py       # Claude API → link_graph.json, then inject <a> anchors
│   └── build_sitemap.py          # zero-API, writes sitemap.xml from keyword_map.json
├── content/                      # one JSON per page (cached body_html, faq, meta…)
│   ├── index.json
│   ├── yacht-charter-marbella.json
│   ├── catamaran-rental-marbella.json
│   ├── boat-rental-no-license-marbella.json
│   ├── blog_how-much-does-it-cost-to-rent-a-boat-in-marbella.json
│   └── blog_boat-license-rules-spain.json
├── link_graph.json               # outbound link map per page (hand-authored MVP; generator overwrites)
├── link_graph_audit.json         # which proposed anchors were actually injected
└── site/                         # deployable output
    ├── index.html
    ├── yacht-charter-marbella/index.html
    ├── catamaran-rental-marbella/index.html
    ├── boat-rental-no-license-marbella/index.html
    ├── blog/how-much-does-it-cost-to-rent-a-boat-in-marbella/index.html
    ├── blog/boat-license-rules-spain/index.html
    ├── styles.css
    ├── robots.txt                # LLM-bot allowlist (GPTBot, ClaudeBot, PerplexityBot, etc.)
    ├── llms.txt                  # GEO citation manifest
    └── sitemap.xml
```

## Run

```bash
# 1. Generate remaining pages (needs ANTHROPIC_API_KEY with credit)
export $(grep -E '^ANTHROPIC_API_KEY=' /Users/mardosoo/aiangels-blog/.env)
python3 scripts/generate_pages.py                 # generates the 13 missing pages
# or
python3 scripts/generate_pages.py --only fishing  # just one slug
python3 scripts/generate_pages.py --force         # regenerate everything

# 2. Re-render HTML only (no API)
python3 scripts/generate_pages.py --render-only

# 3. Build the LLM internal link graph and inject anchors
python3 scripts/build_link_graph.py               # uses link_graph.json if it exists
FORCE_GRAPH=1 python3 scripts/build_link_graph.py # ask Claude for a fresh graph

# 4. Sitemap
python3 scripts/build_sitemap.py

# 5. Preview locally
cd site && python3 -m http.server 8765
open http://localhost:8765/
```

## Deploy

Static — drop `site/` onto any host:
- **GitHub Pages**: copy `site/*` to `mardo89.github.io/boat-rental-marbella/` and set CNAME on the registered domain.
- **Cloudflare Pages**: connect a repo, set `site/` as the output dir.
- **Standalone domain**: A-record to any static host; `boatrentalmarbella.com/.es/.net` to be registered (placeholder used in keyword_map.json).

## Open items (need user input before launch)

1. Register the domain (or change `site.base_url` + `site.domain` in `config/keyword_map.json`).
2. Real WhatsApp + phone number — currently placeholder `+34 600 000 000`. Update `site.phone_e164`, `site.phone_display`, `site.whatsapp_e164` in `config/keyword_map.json`, then re-run `scripts/generate_pages.py --render-only`.
3. Affiliate ID for Click&Boat — replace the placeholder `utm_source` in `site.affiliate_link`.
4. Top up Anthropic credits to generate the 13 remaining pages.
5. OG image (currently `https://boatrentalmarbella.com/og-image.jpg` is broken until the file is created).

## SEO / LLM linking design

- **Hub-and-spoke** with 8 transactional spokes + 10 informational blog posts (see `config/keyword_map.json`).
- **Schema.org JSON-LD** on every page: `LocalBusiness` + (`Service`|`BlogPosting`) + `FAQPage` + `BreadcrumbList`. The competitor uses none.
- **LLM-bot allowlist** in `robots.txt` (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Bytespider, Amazonbot, Applebot-Extended, meta-externalagent) — explicit invitation for GEO citation.
- **`llms.txt`** manifest with site purpose, factual claims (prices, rules, ports), and canonical URL map — designed for retrieval by Perplexity/ChatGPT search.
- **Internal link graph** generated by Claude from page summaries: 5–8 outbound contextual anchors per page, injected into prose (not bulleted footers). Hand-authored MVP graph in `link_graph.json` covers the 6 published pages; re-run `build_link_graph.py` with `FORCE_GRAPH=1` once all 19 pages exist to regenerate.
