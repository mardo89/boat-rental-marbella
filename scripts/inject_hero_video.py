#!/usr/bin/env python3
"""Post-process rendered HTML pages: replace <picture class="hero-img-wrap">
with an autoplay <video class="hero-video"> when the page slug appears in
config/videos.json placement[]. Also strips the duplicate video-section
block from the body if present.

Run after all builders (generate_pages.py, build_boats.py, build_experiences.py,
build_es.py) so the swap applies site-wide.
"""
from __future__ import annotations
import json, pathlib, re, html

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
VIDEOS = json.loads((ROOT / "config" / "videos.json").read_text())["videos"]

# slug-path → video config (first match wins)
PLACEMENT_MAP = {}
for v in VIDEOS:
    for p in (v.get("placement") or []):
        PLACEMENT_MAP.setdefault(p, v)

def already_has_hero_video(s: str) -> bool:
    return 'class="hero-video"' in s

def swap(path: pathlib.Path, video: dict):
    s = path.read_text()
    if already_has_hero_video(s):
        return False
    if 'class="hero-img-wrap"' not in s:
        return False
    title = html.escape(video["title"])
    hero_video = (
        f'<video class="hero-video" autoplay muted loop playsinline '
        f'preload="metadata" poster="/video/{video["slug"]}.jpg" '
        f'aria-label="{title}">'
        f'<source src="/video/{video["slug"]}.mp4" type="video/mp4">'
        f'</video>'
    )
    new = re.sub(
        r'<picture class="hero-img-wrap">[\s\S]*?</picture>',
        hero_video, s, count=1,
    )
    # Strip the duplicate video-section if it shows the same clip
    new = re.sub(
        r'<section class="video-section">[\s\S]*?</section>',
        "", new, count=1,
    )
    if new != s:
        path.write_text(new)
        return True
    return False

def main():
    swapped = 0
    for placement, video in PLACEMENT_MAP.items():
        # placement is like "/", "/boats/", "/boats/azimut-39/"
        rel = placement.strip("/")
        path = (SITE_DIR / rel / "index.html") if rel else (SITE_DIR / "index.html")
        if not path.exists():
            continue
        if swap(path, video):
            swapped += 1
            print(f"  ✓ hero-video → {placement}  ({video['slug']})")
    print(f"inject_hero_video: {swapped} page(s) swapped")

if __name__ == "__main__":
    main()
