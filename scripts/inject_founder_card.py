#!/usr/bin/env python3
"""Inject a sitewide "Founder note" trust card with Andra's video into key
high-trust landing pages. Idempotent — skips pages that already contain it.

Placement rationale: appears on pages where buyers need extra trust before
clicking WhatsApp — homepage, wedding, proposal, luxury yacht, boat-party,
fishing, hub spokes — placed just before the FAQ section (or near the end
of the article body if FAQ isn't present).
"""
from __future__ import annotations
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

CARD_HTML = '''<aside class="founder-card" aria-label="Founder note from Andra Kiirkivi">
  <video controls preload="metadata" playsinline muted poster="/video/andra-founder-note.jpg" width="540" height="960">
    <source src="/video/andra-founder-note.mp4" type="video/mp4">
    Your browser doesn't support HTML5 video.
  </video>
  <div class="founder-meta">
    <strong>Andra Kiirkivi</strong>
    <div class="role">Founder &amp; CEO · Boat Rental Marbella</div>
    <p>"Every booking on this site lands on my phone first. I run the operations end-to-end with our skippers, so the boat you see is the boat that picks you up — same fleet, same crew, no third-party hand-off."</p>
    <p>If anything goes sideways before, during or after your charter, I'm the person you message. Most replies under 5 minutes during Marbella daytime.</p>
    <a class="ig-link" href="https://www.instagram.com/boatrentalmarbella/" rel="noopener" target="_blank">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1.2" fill="currentColor" stroke="none"/></svg>
      Follow @boatrentalmarbella
    </a>
  </div>
</aside>'''

# Pages to inject (relative to /site, end with / for index lookup)
PAGES = [
    "",                                                       # homepage
    "boat-party-marbella/",
    "luxury-yacht-rental-marbella/",
    "yacht-charter-marbella/",
    "fishing-boat-rental-marbella/",
    "sunset-cruise-marbella/",
    "boat-rental-puerto-banus/",
    "boats/",
    "experiences/",
    "experiences/wedding-yacht-marbella/",
    "experiences/proposal-yacht-marbella/",
    "experiences/anniversary-yacht-marbella/",
    "experiences/honeymoon-yacht-marbella/",
    "experiences/birthday-yacht-marbella/",
    "experiences/corporate-yacht-marbella/",
    "experiences/family-boat-days-marbella/",
    "experiences/bachelor-hen-parties-marbella/",
    "experiences/photoshoot-yacht-marbella/",
]

def inject(path: pathlib.Path) -> bool:
    s = path.read_text()
    if "founder-card" in s:
        return False
    # Strategy: insert before the "Frequently asked questions" H2 if present,
    # else before the closing </article> or </main>, else before footer.
    patterns = [
        r'(<h2[^>]*>\s*Frequently asked questions\s*</h2>)',
        r'(<h2[^>]*>\s*Preguntas frecuentes\s*</h2>)',
        r'(</article>)',
        r'(</main>)',
        r'(<footer\b)',
    ]
    for pat in patterns:
        m = re.search(pat, s, re.IGNORECASE)
        if m:
            new = s[:m.start()] + CARD_HTML + "\n" + s[m.start():]
            path.write_text(new)
            return True
    return False

def main():
    n = 0
    for rel in PAGES:
        p = SITE / rel / "index.html" if rel else SITE / "index.html"
        if not p.exists():
            continue
        if inject(p):
            n += 1
            print(f"  ✓ founder-card → /{rel}")
    print(f"inject_founder_card: {n} page(s) updated")

if __name__ == "__main__":
    main()
