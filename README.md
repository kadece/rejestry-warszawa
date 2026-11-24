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
| Bemowo | GUNB + strona dzielnicy | 2016 | 5 471 |
| Białołęka | GUNB | 2016 | 19 800 |
| Bielany | GUNB | 2016 | 5 941 |
| Mokotów | GUNB + strona dzielnicy | 2016 | 13 099 |
| Ochota | GUNB | 2016 | 3 284 |
| Praga-Północ | GUNB + strona dzielnicy | 2016 | 4 581 |
| Praga-Południe | GUNB | 2016 | 6 246 |
| Rembertów | GUNB | 2016 | 2 627 |
| Śródmieście | GUNB + strona dzielnicy | 2016 | 10 744 |
| Targówek | GUNB + strona dzielnicy | 2016 | 6 484 |
| Ursus | strona dzielnicy | 2019 | 4 567 |
| Ursynów | GUNB | 2016 | 7 453 |
| Wawer | GUNB + strona dzielnicy | 2016 | 22 337 |
| Wesoła | GUNB | 2016 | 6 401 |
| Wilanów | GUNB + strona dzielnicy | 2016 | 10 225 |
| Włochy | GUNB | 2016 | 3 004 |
| Wola | GUNB | 2016 | 5 093 |
| Żoliborz | GUNB | 2016 | 2 606 |

**Razem: 139 963 pozycji w 214 plikach rocznikowych (48 MB).**

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
| Bemowo | `bemowo.um.warszawa.pl/jawnosc-procesu-inwestycyjnego` | WZ, ICP, wszczęte postępowania (od 2018) |
| Mokotów | `mokotow.um.warszawa.pl/wykazy-i-informacje-o-decyzjach` + 2 archiwa | wnioski WZ, wnioski ICP, decyzje WZ, decyzje ICP (2018–2026) |
| Praga-Północ | `pragapn.um.warszawa.pl/-/ogloszenia-2` | WZ, ICP, wnioski (od 2021, pliki miesięczne) |
| Śródmieście | `srodmiescie.um.warszawa.pl/-/decyzje-warunki-zabudowy` | WZ (od 2020, pliki miesięczne) |
| Targówek | `targowek.um.warszawa.pl/waw/targowek/-/warunki-zabudowy-postepowania-decyzje` | wnioski WZ/ICP, decyzje WZ, decyzje ICP (od 2021) |
| Ursus | `ursus.um.warszawa.pl/wykazy` | 9 rejestrów (WZ, PnB, LCP, ZRID, wnioski, zgłoszenia, umowy art. 16) |
| Wawer | `wawer.um.warszawa.pl/dokumenty-budowlane` | WZ, ICP/CP (pliki miesięczne, obecnie rocznik bieżący) |
| Wilanów | `wilanow.um.warszawa.pl/waw/wilanow/wykazy-i-informacje-o-decyzjach` | wnioski WZ/ICP, decyzje WZ, decyzje ICP (od 2020, rejestry skumulowane) |

Nie ma wspólnego schematu adresów między dzielnicami — każda publikuje
po swojemu (Bemowo trzyma wszystko na jednej stronie „jawność”, Ursus ma
`/wykazy-za-rok-YYYY`, Praga-Północ wrzuca wszystko do jednego wpisu
`/-/ogloszenia-2` jako ~155 załączników miesięcznych, Śródmieście
`NN_DECYZJE_WZ_YYYY.xlsx`, Wilanów prowadzi cztery rejestry skumulowane
„Zał. 1a/1b/2/3” od 2020 roku). Dlatego każda dzielnica ma osobny adapter
w `districts/<nazwa>.py`.

**Ursus nie korzysta z GUNB** — jego strona publikuje już rejestry PnB,
więc dane z GUNB by się dublowały. Pozostałe dzielnice serwisowe mają
w swoich rejestrach tylko WZ/ICP, więc GUNB dokłada im PnB i niczego
nie dubluje.

---

## Jak to działa

```
build.py
  ├── gunb.py          → pobiera i czyta plik zbiorczy GUNB
  ├── districts/
  │     ├── base.py    → wspólna logika rocznika (pobierz → sparsuj → JSON)
  │     ├── bemowo.py, srodmiescie.py, wawer.py
  │     │             → rejestry WZ/ICP ze stron tych dzielnic
  │     ├── mokotow.py → 4 rejestry (wn/dec WZ i ICP, 2018+, .xls i PDF-y)
  │     ├── targowek.py → wnioski WZ/ICP + decyzje WZ/ICP (od 2021)
  │     ├── wilanow.py → 3 rejestry skumulowane (od 2020, krojone po dacie)
  │     ├── ursus.py   → 9 rejestrów, konfiguracja + dopasowanie plików
  │     └── praga_polnoc.py → 3 rejestry, pliki miesięczne
  └── parsers.py       → XLSX/XLS i PDF → macierz → wiersze
```

Wynik:

```
site/index.html          powłoka strony (22 kB, dane ładowane na żądanie)
site/data/index.json     manifest: dzielnice, roczniki, liczby pozycji
site/data/<slug>/<rok>.json
```

Strona **nie** ma danych w HTML-u — `app.js` pobiera `data/index.json`,
a potem konkretny rocznik. Dzięki temu 46 MB danych nie trafia do jednego
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

Wymagania: Python 3.10+, `openpyxl`, `pdfplumber`, `xlrd`
(stare rejestry `.xls`, np. mokotowskie z lat 2018–2020).

```bash
python -m pip install openpyxl pdfplumber xlrd

python build.py                      # wszystkie dzielnice (≈6 min)
python build.py --gunb-only          # dzielnice bez własnej strony (to robi CI)
python build.py --site-only          # dzielnice serwisowe (to robi update.sh)
python build.py --district ursus     # jedna dzielnica
python build.py --offline            # bez pobierania, z cache w raw/
python build.py --render-only        # tylko HTML z gotowych JSON-ów
python build.py --skip-site          # pomiń strony dzielnic (tylko GUNB)
```

Podgląd lokalny wymaga HTTP — otwarty z `file://` plik nie wczyta danych,
bo przeglądarki blokują `fetch()` po protokole plików („Failed to fetch").
Odpal mini-serwer i wejdź na http://localhost:8000/:

```bash
python -m http.server --directory site
```

Katalog `raw/` to cache pobranych plików (nie trafia do repo). Usunięcie go
wymusza pełne ponowne pobranie ~47 MB z GUNB i kilkuset PDF-ów.

---

## Aktualizacja

Dane odświeżają się dwutorowo, bo `*.um.warszawa.pl` blokuje serwery
GitHuba (HTTP 403), a GUNB — nie:

| Tor | Co buduje | Kiedy |
|---|---|---|
| GitHub Actions | 10 dzielnic z GUNB (~25 MB) | co poniedziałek + po każdym pushu |
| twoja maszyna | 8 dzielnic serwisowych (~27 MB) | `./update.sh`, co dwa tygodnie |

Dzielnice serwisowe (z rejestrami WZ/ICP ze strony dzielnicy) buduje
maszyna lokalna: **Bemowo, Mokotów, Praga-Północ, Śródmieście, Targówek,
Ursus, Wawer i Wilanów**. Pozostałe 10 bierze w CI prosto z pliku GUNB.

Oba piszą do `site/data/` i się nie nadpisują — manifest jest składany
ze skanu katalogu, a każdy tor buduje tylko swoje dzielnice.

Instrukcja krok po kroku: **[AKTUALIZACJA.md](AKTUALIZACJA.md)**.
Samodzielna instrukcja dla serwera (z wpisem do crona):
**[SERWER.md](SERWER.md)**.

Skrót:

```bash
./update.sh          # 8 dzielnic serwisowych → commit → push
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
