#!/usr/bin/env python3
"""Daily content routine — generates N blog/spoke pages per run.

Workflow:
  1. Load config/content_queue.json — queue of {kind, slug, primary_keyword, title, target_words, ...}
  2. Pop the first ITEMS_PER_DAY items
  3. For each: call Claude API to produce the page JSON (body_html + FAQ + meta_description + summary + key_facts), save to content/<slug>.json (or content/blog_<basename>.json for blog posts)
  4. Append entry to config/keyword_map.json (spokes or blog array)
  5. Move the consumed items into queue.consumed
  6. Run scripts/deploy.sh to render → publish → IndexNow ping

Triggered by ~/Library/LaunchAgents/com.boatrentalmarbella.daily-content.plist at 10:00 daily.

Requires: ANTHROPIC_API_KEY env var with non-zero credit balance.
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, sys, subprocess, datetime, traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "config" / "content_queue.json"
KEYWORD_MAP_PATH = ROOT / "config" / "keyword_map.json"
BOATS_PATH = ROOT / "config" / "boats.json"
CONTENT_DIR = ROOT / "content"
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "daily_content.log"

def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")

# ---------- env ----------
def load_env():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for p in [
        ROOT / ".env",
        ROOT.parent.parent / ".env",
        pathlib.Path.home() / "aiangels-blog" / ".env",
    ]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return

load_env()

# Generation backend: "cli" = Claude Code CLI (uses your subscription, no API credit)
#                     "api" = Anthropic API (needs ANTHROPIC_API_KEY credit)
BACKEND = os.environ.get("CLAUDE_BACKEND", "cli")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

def _call_cli(system: str, user: str, timeout_s: int = 600) -> str:
    """Invoke `claude -p` (headless mode). Uses local subscription, not API credit."""
    full = system + "\n\n---\n\nUSER REQUEST:\n\n" + user
    proc = subprocess.run(
        ["claude", "-p", full, "--output-format", "text"],
        capture_output=True, text=True, timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exit {proc.returncode}: {proc.stderr[-300:]}")
    return proc.stdout.strip()

def _call_api(system: str, user: str) -> str:
    from anthropic import Anthropic
    client = Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=8000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()

# ---------- system prompt — short, fleet-aware ----------
def system_prompt():
    keyword_map = json.loads(KEYWORD_MAP_PATH.read_text())
    boats_cfg = json.loads(BOATS_PATH.read_text())
    site = keyword_map["site"]
    boats_summary = "\n".join(
        f"- {b['name']} ({b['length_m']}m, {b['capacity_pax']} pax, departs {b['departure_port']})"
        for b in boats_cfg["boats"]
    )
    return f"""You are an SEO copywriter producing pages for {site['name']}, an affiliate-style guide to chartering boats in Marbella, Spain.

OUR FLEET (use these for fleet-specific claims; never invent specs):
{boats_summary}

PRICING REFERENCE — use only these numbers for our boats:
- Tier A (Astondoa 40, Azimut 39): €749/2h → €2,299/8h (skipper + drinks + VAT included)
- Tier B (Mangusta 80 incl. white/grey variants): €4,719 minimum 4h (jet ski included free)
- Other boats: pricing on request via WhatsApp (do not invent hourly rates)

INCLUSIONS on every charter: licensed skipper, fuel, water + soft drinks + beer + white wine + cava, light snacks, insurance, safety equipment, Spanish IVA (21%).

WRITING STYLE
- Answer-first paragraphs; British English; honest, no fluff.
- Concrete numbers (€, NM, m, kts, °C) — never vague "lots of" or "huge".
- Local colour: Puerto Banús, Marbella Marina, Cabopino, Estepona, Sotogrande, La Concha, Río Verde, Cala del Faro, Cala Cortés, Golden Mile.
- No fabricated testimonials, no made-up reviews.
- Internal links via markdown [anchor](/slug/) — link 4-7 times per piece. Always include one inline link to /  (the hub).
- Do not promote operators other than us. We are not affiliates: our boats are the offering.

OUTPUT — STRICT JSON, no prose, no code fences:
{{
  "meta_description": "<150-160 chars, includes primary keyword + 1 number + a CTA verb>",
  "summary": "<2 sentences for internal-link-graph use>",
  "key_facts": ["<5-8 short bullets, each ≤120 chars>"],
  "faq": [{{"q":"...","a":"..."}}, ... 5-8 Q&A pairs, answers 30-80 words each],
  "body_html": "<full <section>/<h2>/<p>/<ul>/<table>/<details> markup, target word count provided in the user message. Start with an intro <p>, then 5-9 H2 sections, then a 'Frequently asked questions' H2 with <details><summary>question</summary><p>answer</p></details> blocks mirroring the faq array. Never include <h1>, <html>, <head>, <body>, inline CSS, or <script>.>"
}}
"""

def build_user_prompt(item: dict) -> str:
    extra = ""
    if item.get("fleet_focus"):
        extra = f"\nFLEET FOCUS: feature these boats from our fleet: {', '.join(item['fleet_focus'])}.\n"
    return f"""Produce the page for:

TITLE: {item['title']}
PRIMARY KEYWORD: {item['primary_keyword']}
SLUG: /{item['slug']}/ (kind: {item['kind']})
TARGET WORD COUNT: {item.get('target_words', 1200)}
{extra}
Return only the JSON object specified in the system message."""

def generate(item: dict) -> dict:
    system = system_prompt()
    user = build_user_prompt(item) + "\n\nReturn the JSON object only — no prose before or after, no markdown fences."
    raw = _call_cli(system, user) if BACKEND == "cli" else _call_api(system, user)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    # CLI may emit a status line / extra text — extract the JSON object span
    start = raw.find("{")
    end   = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        last = raw.rfind("}")
        return json.loads(raw[:last + 1])

# ---------- file plumbing ----------
def content_filename(slug: str) -> pathlib.Path:
    return CONTENT_DIR / (slug.replace("/", "_") + ".json")

def save_content(item: dict, data: dict):
    fp = content_filename(item["slug"])
    page = {
        "slug": item["slug"],
        "primary_keyword": item["primary_keyword"],
        "title": item["title"],
        "intent": item.get("intent", "informational" if item["kind"] == "blog" else "transactional"),
        "target_words": item.get("target_words", 1200),
    }
    fp.write_text(json.dumps({"page": page, "kind": item["kind"], "data": data}, ensure_ascii=False, indent=2))
    log(f"  ✓ saved {fp.relative_to(ROOT)}")

def add_to_keyword_map(item: dict):
    d = json.loads(KEYWORD_MAP_PATH.read_text())
    entry = {
        "slug": item["slug"],
        "primary_keyword": item["primary_keyword"],
        "title": item["title"],
        "intent": item.get("intent", "informational" if item["kind"] == "blog" else "transactional"),
        "target_words": item.get("target_words", 1200),
    }
    bucket = "blog" if item["kind"] == "blog" else "spokes"
    if not any(s["slug"] == item["slug"] for s in d[bucket]):
        d[bucket].append(entry)
        KEYWORD_MAP_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2))
        log(f"  ✓ added to keyword_map.{bucket}")

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None, help="override items_per_day from queue config")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    queue_cfg = json.loads(QUEUE_PATH.read_text())
    n = args.n or queue_cfg.get("items_per_day", 5)
    queue = queue_cfg.get("queue", [])
    if not queue:
        log("queue empty — nothing to do.")
        return 0
    batch = queue[:n]
    log(f"=== Daily content run: {len(batch)} item(s) ===")

    succeeded, failed = [], []
    for i, item in enumerate(batch, 1):
        log(f"[{i}/{len(batch)}] {item['kind']} · {item['slug']}")
        try:
            if args.dry_run:
                log("  (dry-run, skipping generation)")
                continue
            data = generate(item)
            save_content(item, data)
            add_to_keyword_map(item)
            succeeded.append(item)
        except Exception as e:
            log(f"  ✗ FAILED: {type(e).__name__}: {str(e)[:200]}")
            traceback.print_exc()
            failed.append(item)

    # Move succeeded items from queue → consumed (failures stay in queue head for retry)
    if succeeded and not args.dry_run:
        queue_cfg["queue"] = [q for q in queue if q not in succeeded]
        queue_cfg.setdefault("consumed", []).extend(
            [{**s, "consumed_at": datetime.date.today().isoformat()} for s in succeeded]
        )
        QUEUE_PATH.write_text(json.dumps(queue_cfg, ensure_ascii=False, indent=2))
        log(f"queue: {len(queue_cfg['queue'])} remaining, {len(queue_cfg['consumed'])} consumed total")

    if succeeded and not args.dry_run:
        log("running deploy.sh …")
        proc = subprocess.run(
            ["bash", str(ROOT / "scripts" / "deploy.sh"),
             f"Daily content: +{len(succeeded)} pages ({', '.join(s['slug'] for s in succeeded)})"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if proc.returncode != 0:
            log(f"deploy.sh exited {proc.returncode}: {proc.stderr[-500:]}")
            return 2
        log("deploy.sh OK")

    log(f"=== Done: {len(succeeded)} succeeded, {len(failed)} failed ===\n")
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
