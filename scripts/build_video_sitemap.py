#!/usr/bin/env python3
"""Generate sitemap-video.xml (Google video-sitemap spec) + inject VideoObject
JSON-LD on every page that hosts a video.

Why two layers:
  1. Video sitemap → tells Google which pages host video content, with
     contentUrl, thumbnail, title, description, duration, family-friendly flag.
  2. Per-page VideoObject JSON-LD → required for rich-result eligibility
     (video thumbnail in SERP, "Key moments", etc.).

Reads config/videos.json for canonical metadata; introspects rendered HTML to
discover any <video> tag on a page (so dynamically-injected hero videos and
founder-note videos are both covered).
"""
from __future__ import annotations
import json, pathlib, re, datetime, subprocess, html

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
BASE = CONFIG["site"]["base_url"].rstrip("/")
VIDEOS = json.loads((ROOT / "config" / "videos.json").read_text())["videos"]
TODAY = datetime.date.today().isoformat()

# Static metadata for non-content videos (founder note etc) not in videos.json
STATIC = {
    "andra-founder-note": {
        "title": "Founder note — Andra Kiirkivi, CEO of Boat Rental Marbella",
        "description": "Andra Kiirkivi, founder of Boat Rental Marbella, on how the operation runs end-to-end and what to expect when you book.",
        "tags": ["founder", "Boat Rental Marbella", "CEO", "Andra Kiirkivi"],
    },
}

def video_meta(slug):
    for v in VIDEOS:
        if v["slug"] == slug:
            return v
    if slug in STATIC:
        return {"slug": slug, **STATIC[slug]}
    return None

def probe_duration(mp4_path: pathlib.Path) -> int | None:
    """Return integer seconds. Cached in .video_duration.json to avoid re-running ffprobe."""
    cache_file = ROOT / "config" / ".video_durations.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    key = mp4_path.name
    if key in cache:
        return cache[key]
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(mp4_path)],
            text=True, timeout=10,
        )
        sec = int(float(out.strip()))
        cache[key] = sec
        cache_file.write_text(json.dumps(cache, indent=2))
        return sec
    except Exception:
        return None

def iso_duration(sec: int | None) -> str | None:
    if sec is None or sec <= 0:
        return None
    m, s = divmod(sec, 60)
    if m:
        return f"PT{m}M{s}S"
    return f"PT{s}S"

# ---------------- find which pages host which video ----------------
def discover_video_pages():
    """Returns {page_url: [slug, slug, ...]} by scanning rendered HTML."""
    pat = re.compile(r'src="/video/([a-z0-9\-]+)\.mp4"')
    result = {}
    for html_path in SITE.rglob("index.html"):
        s = html_path.read_text()
        slugs = list(dict.fromkeys(pat.findall(s)))  # unique, order-preserved
        if not slugs:
            continue
        rel = html_path.relative_to(SITE).parent
        page_url = f"{BASE}/" if str(rel) == "." else f"{BASE}/{rel}/"
        result[page_url] = slugs
    return result

# ---------------- video sitemap ----------------
def build_video_sitemap(pages_map):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">']
    for page_url, slugs in sorted(pages_map.items()):
        lines.append(f'  <url>')
        lines.append(f'    <loc>{page_url}</loc>')
        for slug in slugs:
            meta = video_meta(slug) or {"slug": slug, "title": slug.replace("-", " ").title(), "description": ""}
            content_url = f"{BASE}/video/{slug}.mp4"
            thumb_url = f"{BASE}/video/{slug}.jpg"
            title = html.escape(meta.get("title") or slug)
            desc = html.escape(meta.get("description") or title)[:2000]
            dur = probe_duration(SITE / "video" / f"{slug}.mp4")
            tags = (meta.get("tags") or [])[:32]
            lines.append('    <video:video>')
            lines.append(f'      <video:thumbnail_loc>{thumb_url}</video:thumbnail_loc>')
            lines.append(f'      <video:title>{title}</video:title>')
            lines.append(f'      <video:description>{desc}</video:description>')
            lines.append(f'      <video:content_loc>{content_url}</video:content_loc>')
            if dur:
                lines.append(f'      <video:duration>{dur}</video:duration>')
            lines.append('      <video:family_friendly>yes</video:family_friendly>')
            lines.append('      <video:requires_subscription>no</video:requires_subscription>')
            lines.append('      <video:live>no</video:live>')
            lines.append(f'      <video:publication_date>{TODAY}</video:publication_date>')
            for tag in tags:
                lines.append(f'      <video:tag>{html.escape(tag)}</video:tag>')
            lines.append('    </video:video>')
        lines.append('  </url>')
    lines.append('</urlset>')
    (SITE / "sitemap-video.xml").write_text("\n".join(lines) + "\n")

# ---------------- inject VideoObject JSON-LD ----------------
def videoobject_jsonld(slug, page_url, pos=1):
    meta = video_meta(slug) or {"slug": slug, "title": slug, "description": ""}
    dur = iso_duration(probe_duration(SITE / "video" / f"{slug}.mp4"))
    obj = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": meta.get("title") or slug,
        "description": meta.get("description") or meta.get("title") or slug,
        "thumbnailUrl": [f"{BASE}/video/{slug}.jpg"],
        "uploadDate": f"{TODAY}T00:00:00+02:00",
        "contentUrl": f"{BASE}/video/{slug}.mp4",
        "embedUrl": page_url,
        "isFamilyFriendly": True,
        "publisher": {
            "@type": "Organization",
            "name": "Boat Rental Marbella",
            "logo": {"@type": "ImageObject", "url": f"{BASE}/img/brand/logo.png"},
        },
    }
    if dur:
        obj["duration"] = dur
    return obj

def inject_jsonld(pages_map):
    # marker so we can replace cleanly on re-runs
    BEGIN = "<!-- video-jsonld:begin -->"
    END = "<!-- video-jsonld:end -->"
    pat_existing = re.compile(re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END))
    n = 0
    for page_url, slugs in pages_map.items():
        # locate the file
        rel = page_url.replace(BASE, "").strip("/")
        path = (SITE / rel / "index.html") if rel else (SITE / "index.html")
        if not path.exists():
            continue
        scripts = []
        for slug in slugs:
            obj = videoobject_jsonld(slug, page_url)
            scripts.append(f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False, separators=(",",":"))}</script>')
        block = BEGIN + "\n" + "\n".join(scripts) + "\n" + END
        s = path.read_text()
        if pat_existing.search(s):
            s = pat_existing.sub(block, s)
        else:
            s = s.replace("</head>", block + "\n</head>", 1)
        path.write_text(s)
        n += 1
    return n

def main():
    pages_map = discover_video_pages()
    build_video_sitemap(pages_map)
    n_pages = sum(len(v) for v in pages_map.values())
    print(f"sitemap-video.xml: {len(pages_map)} page(s), {n_pages} video embed(s)")
    n = inject_jsonld(pages_map)
    print(f"VideoObject JSON-LD injected on {n} page(s)")

if __name__ == "__main__":
    main()
