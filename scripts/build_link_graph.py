#!/usr/bin/env python3
"""Phase 2: dense LLM-generated internal link graph.

Reads all content/*.json (produced by generate_pages.py), feeds Claude every
page's (slug, title, primary_keyword, summary, key_facts), asks for a contextual
adjacency list of 6–8 outbound links per page with natural anchor text, then
injects those anchors into the rendered site/<slug>/index.html — only into <p>
prose, only when the chosen anchor phrase appears verbatim and is not already
inside an <a>. Writes link_graph.json for audit / re-runs.

Run:
    python3 scripts/build_link_graph.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, sys, html

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("pip install anthropic")

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
SITE_DIR = ROOT / "site"
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
SITE = CONFIG["site"]

def load_env():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for p in [ROOT.parent.parent / ".env", ROOT.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=",1)[1].strip().strip('"').strip("'")
                    return

load_env()
client = Anthropic()
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

def load_pages():
    pages = []
    for f in sorted(CONTENT_DIR.glob("*.json")):
        d = json.loads(f.read_text())
        p = d["page"]; data = d["data"]
        pages.append({
            "slug": "/" + (p["slug"] + "/" if p["slug"] else ""),
            "title": p["title"],
            "primary_keyword": p["primary_keyword"],
            "summary": data.get("summary",""),
            "key_facts": data.get("key_facts", []),
            "kind": d["kind"],
        })
    return pages

GRAPH_PROMPT = """You are building a dense internal-link graph for an SEO-optimised affiliate site about boat rentals in Marbella.

For EACH page below, propose 6–8 outbound contextual links to OTHER pages on the site. For each link, give:
- "to": the target slug (must match exactly one of the listed slugs)
- "anchor": a 2–6 word natural anchor phrase (lowercase unless proper noun) that is likely to ALREADY APPEAR as plain prose somewhere in the source page — pick phrases users actually write, e.g. "yacht charter", "Puerto Banús", "license-free boats", "sunset cruise", "stag party", "fishing charter", "how much it costs". Diversify anchors — never repeat the exact same anchor twice on the same source page.
- "why": one short sentence justifying the topical fit (for audit only)

Constraints:
- No self-links.
- Every page must include exactly ONE link to "/" (the hub) with a contextual anchor like "boat rental Marbella" or "compare all boats".
- Spread inbound links — every target page should appear as a target on at least 4 different source pages (avoid orphans, avoid hub-spoke only).
- Mix transactional ↔ informational (blog ↔ spoke) where natural — blog posts should link to relevant booking spokes, spokes should link to relevant blog explainers.

Return strict JSON, no prose, no code fences:
{
  "graph": {
    "<source_slug>": [
      {"to":"<target_slug>","anchor":"<anchor text>","why":"<reason>"},
      ...
    ],
    ...
  }
}

Pages:
"""

def build_graph(pages):
    pages_blob = json.dumps([{k:v for k,v in p.items() if k!="key_facts"} | {"key_facts": p["key_facts"][:5]} for p in pages], ensure_ascii=False, indent=2)
    msg = client.messages.create(
        model=MODEL, max_tokens=8000,
        messages=[{"role":"user","content": GRAPH_PROMPT + pages_blob}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)["graph"]

# ---------- HTML injection ----------
# match an occurrence of `phrase` inside <p>...</p>, case-insensitive, not already inside an <a>
def inject_links(html_str: str, links: list[dict]) -> tuple[str, list[dict]]:
    applied = []
    for link in links:
        anchor = link["anchor"].strip()
        target = link["to"]
        if not anchor or len(anchor) < 3:
            continue
        # find <p>...</p> blocks and try to insert
        pattern_p = re.compile(r"(<p>)(.*?)(</p>)", flags=re.DOTALL | re.IGNORECASE)
        replaced = False
        def replace_in_paragraph(m):
            nonlocal replaced
            if replaced:
                return m.group(0)
            para = m.group(2)
            # skip paragraphs already linking to this target
            if f'href="{target}"' in para:
                return m.group(0)
            # find anchor word boundary, not inside an existing <a>
            ap = re.compile(r"(?<![A-Za-z0-9])(" + re.escape(anchor) + r")(?![A-Za-z0-9])", flags=re.IGNORECASE)
            for am in ap.finditer(para):
                start, end = am.span()
                # check not inside <a>
                before = para[:start]
                if before.rfind("<a") > before.rfind("</a>"):
                    continue
                new_para = para[:start] + f'<a href="{target}">{am.group(1)}</a>' + para[end:]
                replaced = True
                applied.append({"anchor": am.group(1), "to": target})
                return m.group(1) + new_para + m.group(3)
            return m.group(0)
        new_html = pattern_p.sub(replace_in_paragraph, html_str)
        html_str = new_html
    return html_str, applied

def slug_to_path(slug: str) -> pathlib.Path:
    s = slug.strip("/")
    return SITE_DIR / (s if s else "") / "index.html"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pages = load_pages()
    if not pages:
        sys.exit("no content/*.json — run generate_pages.py first")

    graph_path = ROOT / "link_graph.json"
    if graph_path.exists() and not os.environ.get("FORCE_GRAPH"):
        print("[load] link_graph.json")
        graph = json.loads(graph_path.read_text())["graph"]
    else:
        print(f"[gen]  link graph from {len(pages)} pages…")
        graph = build_graph(pages)
        graph_path.write_text(json.dumps({"graph": graph}, ensure_ascii=False, indent=2))

    audit = {}
    for source_slug, links in graph.items():
        path = slug_to_path(source_slug)
        if not path.exists():
            print(f"[miss] {source_slug} -> {path}")
            continue
        html_str = path.read_text()
        new_html, applied = inject_links(html_str, links)
        audit[source_slug] = {"proposed": len(links), "applied": len(applied), "applied_links": applied}
        if not args.dry_run and new_html != html_str:
            path.write_text(new_html)
        print(f"[link] {source_slug}: {len(applied)}/{len(links)} applied")
    (ROOT / "link_graph_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    # inbound counts
    inbound = {}
    for src, links in graph.items():
        for l in links:
            inbound.setdefault(l["to"], 0)
            inbound[l["to"]] += 1
    print("\ninbound counts:")
    for tgt, n in sorted(inbound.items(), key=lambda x:-x[1]):
        print(f"  {n:>3}  {tgt}")

if __name__ == "__main__":
    main()
