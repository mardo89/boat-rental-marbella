#!/usr/bin/env python3
"""Upload videos from Google Drive to YouTube @BoatRentalInMarbella.

Picks un-uploaded Drive videos, downloads them temporarily, and uploads with
SEO-optimised titles, descriptions and tags based on the folder keyword map.
Vertical videos under 60 s are automatically posted as Shorts.

Usage:
  python3 scripts/post_youtube.py --login          # first-time Drive OAuth
  python3 scripts/post_youtube.py --login-studio   # one-time YouTube Studio login
  python3 scripts/post_youtube.py --dry-run        # show what would be uploaded
  python3 scripts/post_youtube.py --daily          # upload today's quota (default 2)
  python3 scripts/post_youtube.py --daily --limit 6
  python3 scripts/post_youtube.py --status         # show upload history
"""
from __future__ import annotations

import argparse, datetime, json, os, pathlib, struct, sys, tempfile, time

ROOT              = pathlib.Path(__file__).resolve().parents[1]
STATE_PATH        = ROOT / "config" / "youtube_state.json"
KEYWORD_MAP_PATH  = ROOT / "config" / "blogger_keyword_map.json"
LOG_DIR           = ROOT / "logs"
LOG_PATH          = LOG_DIR / "youtube_post.log"
TMP_DIR           = ROOT / "tmp-social"
DRIVE_FOLDER_ID   = "1qEQPlq6084s7eaq2wqTtoTjN5t2yvFlS"
DAILY_LIMIT       = 2
TOKEN_PATH        = pathlib.Path.home() / ".youtube_token.json"
SITE              = "https://boatrentalinmarbella.com"
WHATSAPP          = "358400406194"
CHANNEL_HANDLE    = "@BoatRentalInMarbella"
YOUTUBE_CHANNEL_ID = "UCu75EPcHSqjpjepdR5nq2iQ"
YT_CATEGORY_ID    = "19"
PRIVACY_STATUS    = "public"

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

YT_SESSION_PATH = pathlib.Path.home() / ".youtube_studio_session.json"
YT_PROFILE_DIR  = pathlib.Path.home() / ".youtube_studio_profile"
STUDIO_URL      = f"https://studio.youtube.com/channel/{YOUTUBE_CHANNEL_ID}"
# Bypass YouTube's "unsupported browser" interstitial shown to headless Chrome
STUDIO_URL_AUTO = f"{STUDIO_URL}?approve_browser_access=true"

VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/mpeg", "video/x-matroska", "video/webm",
}

LOG_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)

# ── logging ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a") as fh:
        fh.write(line + "\n")

# ── env ───────────────────────────────────────────────────────────────────────

def load_env():
    for p in [ROOT / ".env", pathlib.Path.home() / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    k = k.strip()
                    if k and k not in os.environ:
                        os.environ[k] = v.strip().strip('"').strip("'")

load_env()

def require_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"ERROR: {name} is not set.")
    return v

# ── Google Drive auth ─────────────────────────────────────────────────────────

_OAUTH_PORT    = 8765
_AUTH_URL_FILE = pathlib.Path("/tmp/yt_auth_url.txt")

def _run_oauth_flow(creds_path: pathlib.Path):
    import http.server, threading, urllib.parse
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), GOOGLE_SCOPES)
    flow.redirect_uri = f"http://localhost:{_OAUTH_PORT}/"
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="select_account consent")
    _AUTH_URL_FILE.write_text(auth_url)

    code_holder: dict = {"code": None}
    server_holder: dict = {}

    class OAuthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code_holder["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>Login complete! Return to Terminal.</h1>")
            threading.Thread(target=server_holder["srv"].shutdown, daemon=True).start()
        def log_message(self, *args): pass

    srv = http.server.HTTPServer(("localhost", _OAUTH_PORT), OAuthHandler)
    server_holder["srv"] = srv
    log(f"Auth URL written to {_AUTH_URL_FILE}")
    log(f"Waiting for browser callback on port {_OAUTH_PORT} …")
    srv.serve_forever()

    if not code_holder["code"]:
        sys.exit("ERROR: OAuth cancelled.")
    flow.fetch_token(code=code_holder["code"])
    _AUTH_URL_FILE.unlink(missing_ok=True)
    return flow.credentials


def get_credentials(force_reauth: bool = False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = None
    if not force_reauth and TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token and not force_reauth:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
        else:
            creds_path = pathlib.Path(require_env("GOOGLE_CREDENTIALS"))
            if not creds_path.exists():
                sys.exit(
                    f"ERROR: GOOGLE_CREDENTIALS not found: {creds_path}\n"
                    "Download the OAuth client JSON from Google Cloud Console."
                )
            creds = _run_oauth_flow(creds_path)
            TOKEN_PATH.write_text(creds.to_json())
    return creds


# ── YouTube Studio login (one-time) ───────────────────────────────────────────

def login_studio():
    """Open a visible Chrome window for one-time YouTube Studio login.

    Uses the real Chrome binary so Google doesn't flag it as a bot.
    Session is stored as JSON via storage_state — persists automatically.
    """
    from playwright.sync_api import sync_playwright
    import time as _time

    YT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    log("Opening Chrome for YouTube Studio login …")
    log("1. Sign in with andra.kiirkivi@gmail.com")
    log("2. Switch to 'Boat Rental In Marbella' channel if prompted")
    log("3. Session saves automatically once Studio loads")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(YT_PROFILE_DIR),
            channel="chrome",
            headless=False,
            slow_mo=50,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--use-mock-keychain", "--password-store=basic"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(STUDIO_URL)

        deadline = _time.time() + 600
        while _time.time() < deadline:
            url = page.url
            log(f"  Current URL: {url[:80]}")
            if "studio.youtube.com" in url:
                if YOUTUBE_CHANNEL_ID not in url:
                    page.goto(STUDIO_URL)
                    _time.sleep(3)
                else:
                    log("  ✓ YouTube Studio confirmed — saving session …")
                    break
            _time.sleep(5)
        else:
            log("ERROR: Timed out waiting for YouTube Studio login.")
            ctx.close()
            return

        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            pass
        _time.sleep(2)
        ctx.storage_state(path=str(YT_SESSION_PATH))
        ctx.close()
    log(f"YouTube Studio session saved → {YT_SESSION_PATH}")


# ── YouTube Studio upload via Playwright ──────────────────────────────────────

def upload_via_studio(video_path: pathlib.Path, title: str,
                      description: str, tags: list[str]) -> str:
    """Upload video to @BoatRentalInMarbella via YouTube Studio automation."""
    from playwright.sync_api import sync_playwright

    if not YT_SESSION_PATH.exists():
        raise RuntimeError(
            "No YouTube Studio session. Run: python3 scripts/post_youtube.py --login-studio"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--use-mock-keychain", "--password-store=basic"],
        )
        ctx = browser.new_context(
            storage_state=str(YT_SESSION_PATH),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # approve_browser_access bypasses "unsupported browser" interstitial
        page.goto(STUDIO_URL_AUTO)
        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        page.wait_for_timeout(2000)

        if "accounts.google.com" in page.url or "signin" in page.url.lower():
            ctx.close()
            browser.close()
            raise RuntimeError(
                "YouTube Studio session expired. "
                "Run: python3 scripts/post_youtube.py --login-studio"
            )

        # Open Create → Upload videos
        create = page.locator(
            "ytcp-button.ytcpAppHeaderCreateIcon, "
            "button[aria-label='Create'], button[aria-label='Looge']"
        )
        create.first.click(timeout=15_000)
        page.wait_for_timeout(1200)

        # JS click to bypass pointer-event interception
        clicked = page.evaluate("""() => {
            const items = document.querySelectorAll('tp-yt-paper-item, [role="menuitem"]');
            for (const el of items) {
                const t = el.textContent || '';
                if (t.includes('leslaadimine') || t.toLowerCase().includes('upload video')) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""")
        if not clicked:
            page.locator("tp-yt-paper-item").first.click(timeout=10_000, force=True)
        page.wait_for_timeout(1000)

        # Attach video file
        page.locator('input[type="file"]').set_input_files(str(video_path))
        log(f"  File attached: {video_path.name}")

        # Wait for title field
        page.wait_for_selector("#title-textarea, ytcp-mention-textbox", timeout=30_000)
        page.wait_for_timeout(2000)

        # Fill title
        title_box = page.locator("#title-textarea #textbox").first
        title_box.click()
        title_box.press("Meta+a")
        title_box.type(title[:100], delay=20)

        # Fill description
        desc_box = page.locator("#description-textarea #textbox").first
        desc_box.click()
        desc_box.fill(description[:5000])

        # Answer "Not made for kids" — required field
        try:
            kids_no = page.locator(
                'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]'
            ).first
            kids_no.wait_for(state="visible", timeout=5000)
            kids_no.click()
        except Exception:
            pass

        # Advance wizard: Details → Elements → Checks → Visibility (3× Next)
        for _ in range(3):
            nxt = page.locator("ytcp-button#next-button").last
            nxt.wait_for(state="visible", timeout=15_000)
            nxt.click()
            page.wait_for_timeout(1500)

        # Set Public visibility
        try:
            public_radio = page.locator(
                'tp-yt-paper-radio-button[name="PUBLIC"], [data-value=PUBLIC]'
            ).first
            public_radio.wait_for(state="visible", timeout=10_000)
            public_radio.click()
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Grab video URL before publish
        video_url = ""
        try:
            link = page.locator("ytcp-video-info a").first
            link.wait_for(state="visible", timeout=5_000)
            href = link.get_attribute("href") or ""
            if "v=" in href:
                video_url = f"https://www.youtube.com/watch?v={href.split('v=')[-1]}"
            elif "shorts/" in href:
                video_url = f"https://youtube.com/shorts/{href.split('shorts/')[-1].split('?')[0]}"
        except Exception:
            pass

        # Wait for upload to finish
        try:
            page.wait_for_selector(
                "ytcp-video-upload-progress:not([uploading])", timeout=600_000
            )
        except Exception:
            page.wait_for_timeout(8000)

        # Publish
        done_btn = page.locator("ytcp-button#done-button").last
        done_btn.wait_for(state="visible", timeout=60_000)
        done_btn.click()
        page.wait_for_timeout(3000)

        # Refresh session
        ctx.storage_state(path=str(YT_SESSION_PATH))
        ctx.close()
        browser.close()
        return video_url


def build_drive_service(creds):
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=creds, cache_discovery=False)

# ── state ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"uploaded": {}}

def save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2))

def is_uploaded(state: dict, file_id: str) -> bool:
    return file_id in state.get("uploaded", {})

def mark_uploaded(state: dict, file_id: str, meta: dict):
    state.setdefault("uploaded", {})[file_id] = {
        **meta,
        "uploaded_at": datetime.datetime.now().isoformat(),
    }

# ── keyword map ───────────────────────────────────────────────────────────────

def load_keyword_map() -> dict:
    if KEYWORD_MAP_PATH.exists():
        raw = json.loads(KEYWORD_MAP_PATH.read_text())
        return {k: v for k, v in raw.items() if not k.startswith("_")}
    return {}

def folder_meta(folder_name: str, keyword_map: dict) -> dict:
    fn_upper = folder_name.strip().upper()
    entry = keyword_map.get(fn_upper)
    if not entry:
        for key in keyword_map:
            if key in fn_upper or fn_upper in key:
                entry = keyword_map[key]
                break
    return entry or {"keyword": "boat rental Marbella", "landing_url": f"{SITE}/", "template": "general", "related": []}

# ── Drive helpers ─────────────────────────────────────────────────────────────

def list_drive_videos(drive, folder_id: str = DRIVE_FOLDER_ID, folder_name: str = "") -> list[dict]:
    results, page_token = [], None
    while True:
        resp = drive.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size, createdTime)",
            pageSize=100, pageToken=page_token,
        ).execute()
        for f in resp.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                results.extend(list_drive_videos(drive, f["id"], f["name"]))
            elif f["mimeType"] in VIDEO_MIMES:
                f["folder_name"] = folder_name
                results.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results

def download_drive_file(drive, file_id: str, dest: pathlib.Path):
    from googleapiclient.http import MediaIoBaseDownload
    import io
    request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(str(dest), mode="wb")
    downloader = MediaIoBaseDownload(fh, request, chunksize=8 * 1024 * 1024)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"\r  downloading … {int(status.progress()*100)}%", end="", flush=True)
    print()

# ── MP4 probe ─────────────────────────────────────────────────────────────────

def _read_box(data: bytes, offset: int) -> tuple[int, str, int]:
    if offset + 8 > len(data): return 0, "", 0
    size = struct.unpack_from(">I", data, offset)[0]
    btype = data[offset+4:offset+8].decode("latin1")
    header_end = offset + 8
    if size == 1:
        if offset + 16 > len(data): return 0, "", 0
        size = struct.unpack_from(">Q", data, offset+8)[0]
        header_end = offset + 16
    elif size == 0:
        size = len(data) - offset
    return size, btype, header_end

def probe_mp4(path: pathlib.Path) -> dict:
    try:
        with open(path, "rb") as f:
            data = f.read(2 * 1024 * 1024)
    except OSError:
        return {}
    result: dict = {}
    def scan(offset: int, end: int, depth: int = 0):
        while offset < end:
            size, btype, hend = _read_box(data, offset)
            if not size: break
            box_end = offset + size
            if btype in ("moov", "trak", "mdia", "minf", "stbl"):
                scan(hend, min(box_end, end), depth + 1)
            elif btype == "mvhd" and "duration_secs" not in result:
                o = hend
                if o < len(data):
                    version = data[o]; o += 4
                    if version == 1:
                        o += 8 + 8; ts = struct.unpack_from(">I", data, o)[0]; o += 4
                        dur = struct.unpack_from(">Q", data, o)[0]; o += 8
                    else:
                        o += 4 + 4; ts = struct.unpack_from(">I", data, o)[0]; o += 4
                        dur = struct.unpack_from(">I", data, o)[0]; o += 4
                    if ts: result["duration_secs"] = dur / ts
            elif btype == "tkhd" and "width" not in result:
                o = hend
                if o < len(data):
                    version = data[o]; o += 4
                    if version == 1: o += 8 + 8 + 4 + 4 + 8
                    else: o += 4 + 4 + 4 + 4 + 4
                    o += 8; o += 2 + 2 + 2 + 2; o += 36
                    if o + 8 <= len(data):
                        w = struct.unpack_from(">I", data, o)[0] >> 16
                        h = struct.unpack_from(">I", data, o+4)[0] >> 16
                        if w > 0 and h > 0:
                            result["width"] = w; result["height"] = h
            offset = box_end
    scan(0, len(data))
    return result

def is_short_video(path: pathlib.Path, file_name: str) -> bool:
    name_lower = file_name.lower()
    if any(k in name_lower for k in ("short", "reel", "vertical", "portrait", "tiktok")):
        return True
    info = probe_mp4(path)
    if not info: return False
    duration = info.get("duration_secs", 9999)
    w = info.get("width", 0); h = info.get("height", 0)
    return duration <= 60 and h > w

# ── metadata ──────────────────────────────────────────────────────────────────

_FOLDER_THEME: dict[str, str] = {
    "WEDDING": "Wedding Yacht Charter", "PROPOSAL": "Romantic Proposal on a Yacht",
    "HEN PARTY": "Hen Party Boat Charter", "FISHING TRIPS": "Sport Fishing Charter",
    "RED TIDE-FISHING BOAT": "Fishing Boat Marbella", "BANDIDO": "Fishing Boat Marbella",
    "DOLPHINES": "Dolphin Watching Cruise", "LAGOON38": "Catamaran Charter Marbella",
    "DUBHE- SMALLEST BOAT": "Small Boat Hire Marbella", "DUBHE SMALL BOAT": "Small Boat Hire Marbella",
    "MARIAH SX21": "Speedboat Rental Marbella", "AZIMUT58": "Luxury Yacht Charter Marbella",
    "P46": "Motor Yacht Charter Marbella", "FAIRLINE TARGA 12M": "Motor Yacht Charter Marbella",
    "FERRETTI 94": "Superyacht Charter Marbella", "K80": "Superyacht Charter Marbella",
    "M 80 WHITE": "Mangusta 80 Superyacht Marbella", "M 80 GREY": "Mangusta 80 Superyacht Marbella",
    "SPEEDBOAT": "Speedboat Charter Marbella", "ME": "Boat Charter Puerto Banús",
    "POSTERS": "Boat Rental Marbella", "WAYNE LINEKER": "Celebrity Boat Charter Marbella",
}

_BASE_TAGS = [
    "boat rental Marbella", "yacht charter Marbella", "Puerto Banús",
    "Marbella yachts", "Costa del Sol", "boat hire Spain",
    "BoatRentalInMarbella", "Marbella", "yachting",
]

def _theme(folder_name: str) -> str:
    fn_upper = folder_name.strip().upper()
    for key, theme in _FOLDER_THEME.items():
        if key in fn_upper or fn_upper in key:
            return theme
    return "Boat Charter Marbella"

def generate_title(folder_name: str, file_name: str, is_short: bool) -> str:
    theme = _theme(folder_name)
    short_tag = " #Shorts" if is_short else ""
    return f"{theme} | Puerto Banús{short_tag}"

def generate_description(folder_name: str, kw_meta: dict, is_short: bool) -> str:
    keyword = kw_meta.get("keyword", "boat rental Marbella")
    landing = kw_meta.get("landing_url", SITE + "/")
    short_line = "\n#Shorts\n" if is_short else ""
    return f"""{short_line}\
Book your {keyword} from Puerto Banús — skipper, fuel, drinks & insurance all included.

👉 {landing}
📲 WhatsApp: https://wa.me/{WHATSAPP}

From intimate sunset cruises to full-day superyacht charters, we cover the entire \
Costa del Sol: Marbella, Estepona, Gibraltar and beyond.

🛥️ Fleet: small boats (no licence needed), motor yachts, catamarans, superyachts
🐬 Activities: dolphin watching, fishing, watersports, weddings, hen parties
📍 Departure: Puerto Banús Marina, Marbella, Spain

{SITE}

#BoatRentalMarbella #YachtCharterMarbella #PuertoBanus #Marbella #CostaDelSol \
#YachtLife #BoatLife #Spain #Mediterranean #Yachting #BoatCharter \
#MarbellaSummer #LuxuryYacht #SummerVibes
"""

def generate_tags(folder_name: str, kw_meta: dict) -> list[str]:
    keyword = kw_meta.get("keyword", "boat rental Marbella")
    extra = [keyword] + [kw for kw, _ in kw_meta.get("related", [])]
    theme = _theme(folder_name)
    tags = _BASE_TAGS + extra + [theme, folder_name.title()]
    seen: set = set(); out: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:15]

# ── daily run ─────────────────────────────────────────────────────────────────

def daily_upload(drive, state: dict, keyword_map: dict, limit: int, dry_run: bool):
    log(f"Scanning Drive for videos (folder {DRIVE_FOLDER_ID}) …")
    all_videos = list_drive_videos(drive)
    log(f"Found {len(all_videos)} video files in Drive")

    pending = [v for v in all_videos if not is_uploaded(state, v["id"])]
    log(f"{len(pending)} videos not yet uploaded to YouTube")

    if not pending:
        log("Nothing to upload today — all Drive videos are already on YouTube.")
        return

    uploaded_today = 0
    consecutive_errors = 0

    for vid in pending:
        if uploaded_today >= limit:
            break

        folder_name = vid.get("folder_name", "") or "_root_"
        kw_meta     = folder_meta(folder_name, keyword_map)
        file_name   = vid["name"]
        file_id     = vid["id"]
        size_mb     = int(vid.get("size", 0)) // (1024 * 1024)

        log(f"Next: '{file_name}' ({size_mb} MB) from folder '{folder_name}'")

        ext      = pathlib.Path(file_name).suffix or ".mp4"
        tmp_path = TMP_DIR / f"yt_upload_{file_id}{ext}"

        if dry_run:
            log(f"[DRY-RUN] Would upload '{file_name}'")
            log(f"[DRY-RUN]   Title: {generate_title(folder_name, file_name, False)}")
            uploaded_today += 1
            continue

        try:
            log(f"  Downloading from Drive …")
            download_drive_file(drive, file_id, tmp_path)

            short       = is_short_video(tmp_path, file_name)
            title       = generate_title(folder_name, file_name, short)
            description = generate_description(folder_name, kw_meta, short)
            tags        = generate_tags(folder_name, kw_meta)
            video_type  = "Short" if short else "video"

            log(f"  Uploading as {video_type}: '{title}'")
            yt_url = upload_via_studio(tmp_path, title, description, tags)
            log(f"  Uploaded: {yt_url or '(no URL captured)'}")

            mark_uploaded(state, file_id, {
                "title": title, "folder": folder_name,
                "is_short": short, "url": yt_url,
            })
            save_state(state)
            uploaded_today += 1
            consecutive_errors = 0

            if uploaded_today < limit:
                time.sleep(5)

        except Exception as e:
            log(f"  ERROR uploading '{file_name}': {e}")
            consecutive_errors += 1
            if consecutive_errors >= 3:
                log("  3 consecutive errors — stopping to avoid cycling all videos.")
                break
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    log(f"Done. Uploaded {uploaded_today} video(s) today.")

# ── status ────────────────────────────────────────────────────────────────────

def show_status(state: dict):
    uploaded = state.get("uploaded", {})
    print(f"\nYouTube upload state: {len(uploaded)} videos uploaded\n")
    for fid, meta in sorted(uploaded.items(),
                             key=lambda x: x[1].get("uploaded_at", ""), reverse=True)[:20]:
        ts = meta.get("uploaded_at", "")[:10]
        short_tag = " [Short]" if meta.get("is_short") else ""
        print(f"  {ts}  {meta.get('title','?')}{short_tag}")
        if meta.get("url"):
            print(f"         {meta['url']}")
    print()

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Post Drive videos to YouTube")
    parser.add_argument("--login",        action="store_true", help="Re-run Drive OAuth")
    parser.add_argument("--login-studio", action="store_true", help="Save YouTube Studio session")
    parser.add_argument("--daily",    action="store_true", help="Upload today's quota")
    parser.add_argument("--dry-run",  action="store_true", help="Print without uploading")
    parser.add_argument("--status",   action="store_true", help="Show upload history")
    parser.add_argument("--limit",    type=int, default=DAILY_LIMIT)
    args = parser.parse_args()

    if args.status:
        show_status(load_state())
        return

    if args.login_studio:
        login_studio()
        return

    log("Starting YouTube uploader")
    creds = get_credentials(force_reauth=args.login)

    if args.login:
        log("Drive login complete — token saved.")
        log("Next: run --login-studio to save the YouTube Studio session.")
        return

    drive  = build_drive_service(creds)
    state  = load_state()
    kw_map = load_keyword_map()

    if args.daily or args.dry_run:
        daily_upload(drive, state, kw_map, limit=args.limit, dry_run=args.dry_run)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
