# Rejestry i wykazy — dzielnice Warszawy

Przeglądarka decyzji administracyjnych wydawanych przez urzędy dzielnic
Warszawy: pozwoleń na budowę, decyzji o warunkach zabudowy, decyzji o
lokalizacji inwestycji celu publicznego, zgłoszeń robót i wniosków.

**Strona:** https://kadece.github.io/rejestry-warszawa/

Projekt jest rozszerzeniem [rejestry-ursus](https://kadece.github.io/rejestry-ursus/)
na wszystkie 18 dzielnic. Tamten serwis pozostaje bez zmian.

---

## Co jest w środku

| Dzielnica | Źródła | Od roku | Pozycji |
|---|---|---:|---:|
| Bemowo | GUNB | 2016 | 3 582 |
| Białołęka | GUNB | 2016 | 19 796 |
| Bielany | GUNB | 2016 | 5 941 |
| Mokotów | GUNB | 2016 | 11 091 |
| Ochota | GUNB | 2016 | 3 284 |
| Praga-Północ | GUNB + strona dzielnicy | 2016 | 4 581 |
| Praga-Południe | GUNB | 2016 | 6 240 |
| Rembertów | GUNB | 2016 | 2 609 |
| Śródmieście | GUNB | 2016 | 10 218 |
| Targówek | GUNB | 2016 | 6 082 |
| Ursus | strona dzielnicy | 2019 | 4 567 |
| Ursynów | GUNB | 2016 | 7 447 |
| Wawer | GUNB | 2016 | 20 846 |
| Wesoła | GUNB | 2016 | 6 401 |
| Wilanów | GUNB | 2016 | 8 710 |
| Włochy | GUNB | 2016 | 3 004 |
| Wola | GUNB | 2016 | 5 077 |
| Żoliborz | GUNB | 2016 | 2 606 |

**Razem: 132 082 pozycje w 195 plikach rocznikowych (43 MB).**

---

## Skąd dane

### 1. GUNB — pozwolenia na budowę (wszystkie dzielnice, 2016–2026)

Główny Urząd Nadzoru Budowlanego publikuje co noc pliki zbiorcze całego
kraju:

```
https://wyszukiwarka.gunb.gov.pl/pliki_pobranie/wynik_mazowieckie.zip
```

Plik ma ~47 MB (po rozpakowaniu ~334 MB CSV, 31 kolumn, separator `;`,
UTF-8 z BOM). Zawiera wszystkie decyzje z Mazowsza od 2016 roku — dzielnicę
rozpoznajemy po kolumnie `nazwa_organu`, np.
`Prezydent Miasta Warszawa - Praga Pn.`.

Z tego źródła bierzemy dwa rejestry:

* `wn_pnb` — wnioski o pozwolenie na budowę,
* `dec_pnb` — decyzje o pozwoleniu na budowę.

**Uwaga:** wyszukiwarka na stronie GUNB jest chroniona CAPTCHA i nie da się
jej zautomatyzować. Plik zbiorczy to jedyna droga.

### 2. Strony dzielnic — WZ i ICP (tylko tam, gdzie publikują)

| Dzielnica | Adres | Rejestry |
|---|---|---|
| Ursus | `ursus.um.warszawa.pl/wykazy` | 9 rejestrów (WZ, PnB, LCP, ZRID, wnioski, zgłoszenia, umowy art. 16) |
| Praga-Północ | `pragapn.um.warszawa.pl/-/ogloszenia-2` | 3 rejestry (WZ, ICP, wnioski WZ) |

Nie ma wspólnego schematu adresów między dzielnicami — Ursus ma
`/wykazy-za-rok-YYYY`, Praga-Północ wrzuca wszystko do jednego wpisu
`/-/ogloszenia-2` jako 155 załączników miesięcznych.

**Ursus nie korzysta z GUNB** — jego strona publikuje już rejestry PnB,
więc dane z GUNB by się dublowały.

---

## Jak to działa

```
build.py
  ├── gunb.py          → pobiera i czyta plik zbiorczy GUNB
  ├── districts/
  │     ├── base.py    → wspólna logika rocznika (pobierz → sparsuj → JSON)
  │     ├── ursus.py   → 9 rejestrów, konfiguracja + dopasowanie plików
  │     └── praga_polnoc.py → 3 rejestry, pliki miesięczne
  └── parsers.py       → XLSX i PDF → macierz → wiersze
```

Wynik:

```
site/index.html          powłoka strony (22 kB, dane ładowane na żądanie)
site/data/index.json     manifest: dzielnice, roczniki, liczby pozycji
site/data/<slug>/<rok>.json
```

Strona **nie** ma danych w HTML-u — `app.js` pobiera `data/index.json`,
a potem konkretny rocznik. Dzięki temu 43 MB danych nie trafia do jednego
pliku, a przeglądarka ściąga tylko to, co użytkownik otworzy.

### Parsowanie

`parsers.py` obsługuje arkusze i PDF-y jedną ścieżką:

1. `read_matrix()` — XLSX przez openpyxl, PDF przez pdfplumber,
2. `find_header()` — szuka wiersza z „Lp.” (urząd zmienia numer wiersza
   między rocznikami),
3. `build_headers()` — scala dwuwierszowe nagłówki,
4. `parse_matrix()` — wiersze → `{'d': 'RRRR-MM-DD', 'c': {...}}`.

Dwie pułapki, które parser obsługuje:

* **scalone komórki Lp. w PDF-ach** — numer jest tylko w pierwszym wierszu
  tabeli, kolejne mają puste Lp. Parser akceptuje takie wiersze po pierwszym
  numerowanym (inaczej gubił 121 z 122 decyzji WZ z 2019 roku),
* **podmienione pliki** — Ursus opublikował rejestr zgłoszeń pod nazwą
  `rejestr_wnioskow_lcp_2019.pdf`. Parser sprawdza tytuł w treści PDF-a
  (`pdf_title` w konfiguracji rejestru) i odrzuca obcy dokument.

---

## Uruchomienie lokalne

Wymagania: Python 3.10+, `openpyxl`, `pdfplumber`.

```bash
python -m pip install openpyxl pdfplumber

python build.py                      # wszystkie dzielnice (≈6 min)
python build.py --district ursus     # jedna dzielnica
python build.py --offline            # bez pobierania, z cache w raw/
python build.py --render-only        # tylko HTML z gotowych JSON-ów
python build.py --skip-site          # pomiń strony dzielnic (tylko GUNB)
```

Potem otwórz `site/index.html` — działa też z `file://`, bo dane lecą
przez `fetch()` z tego samego katalogu.

Katalog `raw/` to cache pobranych plików (nie trafia do repo). Usunięcie go
wymusza pełne ponowne pobranie ~47 MB z GUNB i kilkuset PDF-ów.

---

## Aktualizacja

Serwery GitHuba dostają **HTTP 403** od `*.um.warszawa.pl`, więc workflow
w `.github/workflows/update.yml` tylko publikuje to, co już leży w repo.
Świeże dane musi wgrać maszyna z dostępem do stron dzielnic.

Instrukcja krok po kroku: **[AKTUALIZACJA.md](AKTUALIZACJA.md)**.

Skrót:

```bash
./update.sh          # pobiera, parsuje, commituje i pushuje
```

---

## Dodanie kolejnej dzielnicy

1. Sprawdź, czy dzielnica publikuje WZ/ICP na swojej stronie. Jeśli nie —
   wystarczy wpis w `DISTRICTS` w `build.py` (dane z GUNB są już gotowe).
2. Jeśli publikuje: skopiuj `districts/praga_polnoc.py`, popraw `BASE`,
   `PAGES`, `REGISTERS` i `list_sources()`.
3. Dopisz `site=<moduł>` w `DISTRICTS`.
4. `python build.py --district <slug>`.

Dzielnice bez własnej strony nie wymagają żadnego kodu — GUNB ma je
wszystkie.

---

## Licencja danych

Dane pochodzą z publicznych rejestrów urzędów dzielnic Warszawy i GUNB.
Projekt je tylko porządkuje i udostępnia w wygodniejszej formie.
