#!/usr/bin/env bash
# Aktualizacja rejestrów Ursusa i Pragi-Północ.
#
# Tylko te dwie dzielnice wymagają własnej maszyny — serwery GitHuba
# dostają od *.um.warszawa.pl HTTP 403. Pozostałe 16 dzielnic buduje
# workflow w .github/workflows/update.yml prosto z pliku GUNB.
#
# Użycie:
#   ./update.sh              # Ursus + Praga-Północ
#   ./update.sh ursus        # jedna dzielnica (do testów)
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

echo "== zależności =="
"$PY" -m pip install --quiet --upgrade openpyxl pdfplumber

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

git add site/data/ursus site/data/praga-polnoc site/data/index.json

if git diff --cached --quiet; then
    echo "== brak zmian w danych — nic nie commituję =="
    exit 0
fi

echo "== zmiany w danych =="
git diff --cached --stat | tail -n 8

git -c user.name="rejestry-bot" \
    -c user.email="rejestry-bot@users.noreply.github.com" \
    commit -m "Aktualizacja Ursus i Praga-Północ $(date +%Y-%m-%d)"
git push

echo
echo "== gotowe — GitHub Pages opublikuje stronę w ciągu ~1 minuty =="
