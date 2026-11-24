# AGENTS.md — rejestry-warszawa (baza wiedzy operacyjnej)

Twarde fakty dla każdego agenta (i człowieka) pracującego nad tym repo.
Kontekst projektowy: patrz README.md, procedury: AKTUALIZACJA.md i SERWER.md.

## Narzędzia na tej maszynie (Windows, użytkownik Krzysztof)

- git: `C:\Users\Krzysztof\AppData\Local\hermes\tools\git-2.56.1+1-win32-x64\bin\git.exe` (brak w PATH)
- bash: `...\git-2.56.1+1-win32-x64\bin\bash.exe`
- gh CLI: `...\git-2.56.1+1-win32-x64\ucrt64\bin\gh.exe` (zalogowany jako kadece)
- Python: `C:\Users\Krzysztof\AppData\Local\Programs\Python\Python312\python.exe`
  (w bashu `python3` to ŚLEPY shim Microsoft Store — zawsze podawać `PYTHON=`)
- podgląd lokalny: `python -m http.server --directory site` → http://localhost:8000
  (nie `file://` — przeglądarka blokuje fetch po protokole plików)

## Poświadczenia i push (ważne!)

- Repo `.git/config` ma w `[credential]`: pusty `helper =` (RESET łańcucha,
  wyłącza systemowego GCM Hermesa, który wywodzi okno wyboru) + helper
  `!C:/.../gh.exe auth git-credential` (token gh z keyring, scope `repo`).
  Dzięki temu `git push` działa bez interakcji — też z automatu.
- Token gh **nie ma scope `workflow`**: push dotykający `.github/workflows/*`
  zostanie odrzucony. Poprawka wymaga `gh auth refresh -s workflow`
  (interaktywne, w przeglądarce). Z tego powodu komentarze w update.yml
  („16 dzielnic…") są celowo nieaktualne — plik działa, bo wybór dzielnic
  jest dynamiczny w build.py (--gunb-only / --site-only).
- PowerShell 5.1 **gubi puste argumenty** komend natywnych:
  `git config key ''` NIE zapisze pustej wartości (robi read-mode!).
  Pusty wpis doczepiać edycją pliku albo przez cmd.

## Automat dzielnic serwisowych — REALNY setup (nie Linux, nie crontab)

- Harmonogram zadań Windows: `Rejestry-Warszawa-Update`,
  **1. i 15. dnia miesiąca o 06:00**, StartWhenAvailable (nadrabia
  pominięte starty), limit 2 h, „tylko gdy sieć dostępna",
  okno ukryte (start przez wscript).
- Wrapper: `C:\Users\Krzysztof\AppData\Local\rejestry-warszawa\
  update-warszawa.bat` (+ `update-warszawa-silent.vbs` jako ukrywacz),
  log: `...\rejestry-warszawa\update.log` (każdy przebieg ze znacznikiem
  czasu i końcowym statusem).
- Wymuszenie ręczne: `schtasks /run /tn Rejestry-Warszawa-Update`.
- update.sh ustawia `PYTHON=` na prawdziwego Pythona, buduje
  `build.py --site-only` (8 dzielnic serwisowych), commituje
  (bot: rejestry-bot) i pcha do origin; CI wtedy przebudowuje
  10 dzielnic GUNB i publikuje Pages.
- Stare zadania NIE NASZE, nie ruszać: `Rejestry-Ursus-Daemon-dzien5/
  dzien20` (zamrożony rejestry-ursus, 5./20. 06:00), `Rejestry-Urbanistyczne-
  Runner` (miesięczny raport mailowy z .vibe promptem), `Inwestycje-Ursus-
  Runner`, + `rejestry-ursus-daemon.bat` w Startup.

## Architektura (dwutorowo)

- CI (GitHub Actions update.yml): push (filtr ścieżek: site/**, build.py,
  gunb.py, parsers.py, districts/**, templates/**) + cron `0 4 * * 1`
  (poniedziałek 04:00 UTC) + workflow_dispatch. Buduje 10 dzielnic z GUNB,
  deploy artefaktu na Pages. README/SERWER.md nie podlegają workflow.
- Lokalnie: 8 dzielnic serwisowych (bemowo, mokotow, praga-polnoc,
  srodmiescie, targowek, ursus, wawer, wilanow) — um.warszawa.pl blokuje
  (403) serwery GitHuba.
- GUNB zip cache: 20 h (gunb.py, max_age_h); verify_ssl=False w gunb.py
  jest CELLOWE (self-signed w łańcuchu gunb.gov.pl).

## Stan danych (2026-11-24, po wdrożeniu 8a3c00f/52a1b29)

- **139 963 pozycji, 18 dzielnic, 214 plików** (~48 MB). Origin = lokalne main.
- Rejestry (2024–2026): bemowo 5, mokotów 6 (wn+dec WZ i ICP), praga-pn 5,
  śródmieście 3 (źródło ma tylko dec_wz), targówek 5, ursus 6–8 (własne
  PnB, gunb=False), wawer 5 (tylko rok bieżący — strona kasuje starsze
  miesięczniki), wilanów 5; 10 dzielnic czysto-GUNB: 2.
- Włochy: 2 rejestry GUNB (3 004 poz.) — strona rejestrowa nie istnieje
  online; jeśli user poda URL — można dorobić adapter.

## Pułapki parsowania (znane, obsłużone — nie „naprawiać" bez sprawdzenia)

- Mokotów: 4 dialekty nagłówków (stare .xls z datą+znakiem w jednej komórce,
  2025 miesięczne bez kolumny Lp., etc.); pliki łączone WZ+CP rozdzielane
  per wiersz filtrem `\bwz\b`/`\bcp\b` (att['nr_filter']); literówka urzędu
  „WZ_07_2027.pdf" = lipiec 2026 — pomijany (setter: year_from_name).
- Wilanów: rejestry skumulowane „Zał. 1a/1b/2/3" od 2020, preferowany XLSX,
  roczniki krajone po dacie wiersza (by_date_year).
- Targówek: „12-2022.pdf" to plik ROCZNY mimo nazwy miesiąca.
- Ursus: publikuje czasem inny dokument pod nazwą rejestru (pdf_title check).
- Daty: komórki literówek („10.12.2128") → nulowane (parser: 2000–2100).

## Weryfikacja po każdej większej zmianie

1. Pełny build lokalnie (bez flag) — czysty log: żadnych `!`, jedynie
   `pominięto… (brak pliku)` tam, gdzie źródło nie publikuje.
2. Porównanie z Pages: pobrać `https://kadece.github.io/rejestry-warszawa/
   data/index.json` i pliki roczne; żaden (dzielnica, rok) nie może mieć
   mniej pozycji niż origin. Wolno więcej.
3. Podgląd :8000; sanity-check kilku roczników (daty, nr, brak wierszy z samym junk).

## Historia w skrócie

- 626e5f4 stopka → 8a3c00f (Mokotów/Targówek/Wilanów + parsery, 139 963)
  → 52a1b29 (pierwszy automatyczny przebieg update.sh) → 938218e
  (update.sh dodaje site/index.html do commita).
