#!/usr/bin/env bash
# Rebuild site → commit → push main → publish to gh-pages branch.
# Run from project root: ./scripts/deploy.sh "commit message"
set -euo pipefail
cd "$(dirname "$0")/.."

MSG="${1:-site update}"

echo "→ render"
python3 scripts/generate_pages.py --render-only > /dev/null
python3 scripts/build_link_graph.py > /dev/null 2>&1 || true
python3 scripts/build_boats.py
python3 scripts/build_blog_index.py
python3 scripts/build_experiences.py
python3 scripts/build_es.py
python3 scripts/build_sitemap.py
python3 scripts/inject_hero_video.py
python3 scripts/inject_founder_card.py
python3 scripts/build_video_sitemap.py

echo "→ commit main"
git add -A
if git diff --cached --quiet; then
  echo "  (no source changes)"
else
  git -c user.name="mardo89" -c user.email="mardo89@users.noreply.github.com" commit -m "$MSG" --quiet
  git push origin main
fi

echo "→ publish gh-pages"
git subtree push --prefix=site origin gh-pages

echo "→ live at https://boatrentalinmarbella.com"

echo "→ IndexNow ping (Bing, Yandex, Naver, Seznam)"
# Wait briefly for CDN to serve new HTML before submitting
sleep 8
python3 scripts/indexnow.py --changed || true

echo "→ Google Indexing API (URL_UPDATED for changed pages)"
python3 scripts/google_index.py --changed || true
