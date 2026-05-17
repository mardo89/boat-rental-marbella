#!/usr/bin/env python3
"""Submit all sitemap URLs to IndexNow (Bing, Yandex, Naver, Seznam).

Detection logic: by default submits every URL in sitemap.xml. With --changed,
parses git diff HEAD~1 HEAD to submit only URLs whose HTML changed.

Usage:
    python3 scripts/indexnow.py            # submit all sitemap URLs
    python3 scripts/indexnow.py --changed  # only URLs whose HTML changed in last commit
"""
from __future__ import annotations
import argparse, json, pathlib, re, subprocess, sys, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY_FILE = ROOT / ".indexnow_key"
SITE_DIR = ROOT / "site"
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
BASE_URL = CONFIG["site"]["base_url"].rstrip("/")
HOST = BASE_URL.replace("https://","").replace("http://","")

def load_key():
    if not KEY_FILE.exists():
        sys.exit(f"missing {KEY_FILE} — generate one with `python3 -c \"import secrets; print(secrets.token_hex(16))\"` and put it there + site/<key>.txt")
    return KEY_FILE.read_text().strip()

def all_sitemap_urls():
    sm = SITE_DIR / "sitemap.xml"
    return re.findall(r"<loc>([^<]+)</loc>", sm.read_text())

def changed_urls():
    # git diff HEAD~1 HEAD --name-only -- site/**/index.html
    try:
        out = subprocess.check_output(
            ["git", "diff", "HEAD~1", "HEAD", "--name-only"],
            cwd=ROOT, text=True
        )
    except subprocess.CalledProcessError:
        return all_sitemap_urls()
    urls = []
    for line in out.splitlines():
        if not line.startswith("site/") or not line.endswith("index.html"):
            continue
        rel = line[len("site/"):-len("index.html")]
        url = f"{BASE_URL}/{rel}"
        urls.append(url)
    return urls or all_sitemap_urls()

def submit(urls, key):
    if not urls:
        print("no urls to submit")
        return
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASE_URL}/{key}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        "https://api.indexnow.org/IndexNow",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"IndexNow {r.status} — submitted {len(urls)} URLs")
            for u in urls:
                print(f"  • {u}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"IndexNow {e.code}: {body}")
    except Exception as e:
        print(f"IndexNow error: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", action="store_true",
                    help="only submit URLs whose HTML changed in the last commit")
    args = ap.parse_args()
    key = load_key()
    urls = changed_urls() if args.changed else all_sitemap_urls()
    submit(urls, key)

if __name__ == "__main__":
    main()
