#!/usr/bin/env bash
# Aktualizacja dzielnic serwisowych: Bemowo, Śródmieście, Wawer,
# Ursus, Praga-Północ, Mokotów, Targówek i Wilanów — czyli tych,
# których rejestry WZ/ICP bierzemy ze stron dzielnic
# (um.warszawa.pl zwraca serwerom GitHuba HTTP 403).
# Dzielnice pozostałe buduje z GUNB workflow w .github/workflows/
# update.yml — nie nadpisuj ich pełnym buildem.
#
# Użycie:
#   ./update.sh              # wszystkie dzielnice serwisowe
#   ./update.sh ursus        # jedna dzielnica (do testów)
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

# katalogi danych dzielnic serwisowych — zgadzają się z DISTRICTS
# w build.py (wpisy z site=...)
SITE_DISTRICTS=(
    "bemowo"
    "srodmiescie"
    "wawer"
    "ursus"
    "praga-polnoc"
    "mokotow"
    "targowek"
    "wilanow"
)

echo "== zależności =="
"$PY" -m pip install --quiet --upgrade openpyxl pdfplumber xlrd

echo
echo "== pobieranie i parsowanie =="
if [ $# -ge 1 ]; then
    "$PY" build.py --district "$1"
else
    "$PY" build.py --site-only
fi

echo
echo "== porządki =="
rm -rf __pycache__ districts/__pycache__

git add $(
    for dist in "${SITE_DISTRICTS[@]}"; do
        echo "site/data/$dist"
    done
) site/data/index.json site/index.html

if git diff --cached --quiet; then
    echo "== brak zmian w danych — nic nie commituję =="
    exit 0
fi

echo "== zmiany w danych =="
git diff --cached --stat | tail -n 8

git -c user.name="rejestry-bot" \
    -c user.email="rejestry-bot@users.noreply.github.com" \
    commit -m "Aktualizacja dzielnic serwisowych $(date +%Y-%m-%d)"
git push

echo
echo "== gotowe — GitHub Pages opublikuje stronę w ciągu ~1 minuty =="
