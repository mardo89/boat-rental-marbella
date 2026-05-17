#!/usr/bin/env python3
"""Download → web-optimise → poster → publish videos from the Drive folder.

Reads config/videos.json (see below for schema) which maps each video clip to
(a) the Drive file ID, (b) a slug, (c) optional watermark-crop flag, (d) the
target page(s) where it should be embedded.

Output per clip:
    site/video/<slug>.mp4     # H.264, AAC, ~2 Mbps, max 720p short-edge
    site/video/<slug>.jpg     # poster (1280w, center frame)

Then the renderer (generate_pages.py / build_boats.py) reads videos.json and
injects the <video> tag + VideoObject JSON-LD on the matching pages.

Usage:
    python3 scripts/process_videos.py            # process any clips not yet processed
    python3 scripts/process_videos.py --force    # re-encode everything
    python3 scripts/process_videos.py --only s1  # one slug
"""
from __future__ import annotations
import argparse, json, pathlib, subprocess, sys, urllib.request, urllib.error, shlex

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config" / "videos.json"
VIDEO_DIR = ROOT / "site" / "video"
TMP_DIR = ROOT / "tmp-videos"

DRIVE_DL = "https://drive.usercontent.google.com/download?id={id}&export=download&authuser=0&confirm=t"

def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)

def fetch_drive(file_id, dest):
    url = DRIVE_DL.format(id=file_id)
    print(f"  ↓ {file_id}")
    urllib.request.urlretrieve(url, dest)

def probe(path):
    out = run("ffprobe", "-v", "quiet", "-print_format", "json",
              "-show_format", "-show_streams", str(path)).stdout
    d = json.loads(out)
    v = next((s for s in d.get('streams', []) if s.get('codec_type') == 'video'), {})
    return {
        "duration": float(d['format'].get('duration', 0)),
        "width": int(v.get('width', 0)),
        "height": int(v.get('height', 0)),
        "codec": v.get('codec_name', ''),
    }

def encode(src, dst, crop_bottom_pct=0):
    """H.264 mp4 with faststart, max 720px short edge, ~2 Mbps."""
    info = probe(src)
    W, H = info['width'], info['height']
    # Build filter chain
    vf = []
    if crop_bottom_pct > 0:
        # Crop the bottom N% (where the operator watermark sits)
        keep_h = int(H * (1 - crop_bottom_pct / 100))
        # Round to nearest even number (H.264 requires even dimensions)
        keep_h -= keep_h % 2
        vf.append(f"crop={W}:{keep_h}:0:0")
        H = keep_h
    # Scale: short edge = 720 (portrait → 720 wide; landscape → 720 tall)
    if W < H:
        target_w = 720
        target_h = int(H * (720 / W))
        target_h -= target_h % 2
        vf.append(f"scale={target_w}:{target_h}")
    else:
        target_h = 720
        target_w = int(W * (720 / H))
        target_w -= target_w % 2
        vf.append(f"scale={target_w}:{target_h}")
    vf_str = ",".join(vf)
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf_str,
        "-c:v", "libx264", "-preset", "slow", "-crf", "26",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        str(dst),
    ]
    print(f"  ▶ encode {' '.join(shlex.quote(c) for c in cmd[-4:])}")
    run(*cmd)

def poster(src, dst, mid_offset=True):
    info = probe(src)
    t = info['duration'] / 2 if mid_offset else 0.5
    run("ffmpeg", "-y", "-ss", str(t), "-i", str(src),
        "-vframes", "1", "-vf", "scale=-2:1280", "-q:v", "3", str(dst))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="slug filter")
    args = ap.parse_args()

    if not CFG_PATH.exists():
        sys.exit(f"missing {CFG_PATH} — write a videos.json first")
    cfg = json.loads(CFG_PATH.read_text())
    TMP_DIR.mkdir(exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    for clip in cfg["videos"]:
        slug = clip["slug"]
        if args.only and args.only not in slug:
            continue
        mp4 = VIDEO_DIR / f"{slug}.mp4"
        jpg = VIDEO_DIR / f"{slug}.jpg"
        if mp4.exists() and jpg.exists() and not args.force:
            print(f"[skip] {slug} (cached)")
            continue
        print(f"[gen]  {slug}")
        raw = TMP_DIR / f"{slug}.raw.mp4"
        if not raw.exists() or args.force:
            fetch_drive(clip["drive_id"], raw)
        encode(raw, mp4, crop_bottom_pct=clip.get("crop_bottom_pct", 0))
        poster(mp4, jpg)
        info = probe(mp4)
        size = mp4.stat().st_size
        print(f"  ✓ {info['width']}x{info['height']} · {info['duration']:.1f}s · {size//1024} KB → {mp4.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
