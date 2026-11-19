# Aktualizacja rejestrów — instrukcja

Dane odświeżają się **dwutorowo**. To nie jest komplikacja bez powodu —
wynika z tego, kto może pobrać co.

```
┌─ GitHub Actions (co tydzień, automatycznie) ──────────────────┐
│  16 dzielnic, dane z pliku zbiorczego GUNB                    │
│  wyszukiwarka.gunb.gov.pl jest z runnerów dostępna            │
│  → build.py --gunb-only → publikacja na Pages                 │
└───────────────────────────────────────────────────────────────┘

┌─ twoja maszyna (co dwa tygodnie, ./update.sh) ────────────────┐
│  Ursus + Praga-Północ, dane ze stron dzielnic                 │
│  *.um.warszawa.pl zwraca runnerom HTTP 403                    │
│  → build.py --site-only → commit + push → Pages przebuduje    │
└───────────────────────────────────────────────────────────────┘
```

Oba tory piszą do `site/data/` i **się nie nadpisują**: manifest
(`site/data/index.json`) jest składany ze skanu katalogu, a każdy tor
buduje tylko swoje dzielnice.

Wielkości: 16 dzielnic z GUNB to ~41 MB, Ursus i Praga-Północ ~2,4 MB.
Dlatego te 41 MB nigdy nie przechodzi przez twoje łącze — generuje je CI.

---

## Co musisz zrobić raz

### 1. Włącz GitHub Pages

**To musisz kliknąć sam** — token GitHuba nie ma uprawnień do utworzenia
strony (`Resource not accessible by integration`).

1. Wejdź na https://github.com/kadece/rejestry-warszawa/settings/pages
2. **Source** → wybierz **GitHub Actions**
3. Zapisz

Bez tego kroku workflow pada na „Konfiguracja GitHub Pages”.

### 2. Sprawdź, czy workflow przechodzi

https://github.com/kadece/rejestry-warszawa/actions/workflows/update.yml

Powinny być dwa zielone joby: `build` i `deploy`. Strona będzie pod
https://kadece.github.io/rejestry-warszawa/

### 3. Przygotuj maszynę do Ursusa i Pragi-Północ

Wymagania: Python 3.10+, `git` z dostępem do repo.

```bash
git clone https://github.com/kadece/rejestry-warszawa.git
cd rejestry-warszawa
python3 -m pip install openpyxl pdfplumber
chmod +x update.sh

# próba na jednej dzielnicy
./update.sh ursus
```

Sprawdzenie dostępu do źródeł:

```bash
curl -sI https://ursus.um.warszawa.pl/wykazy | head -1
curl -sI https://pragapn.um.warszawa.pl/-/ogloszenia-2 | head -1
```

Obie powinny zwrócić `200`. Jeśli `403` — ta maszyna też jest blokowana
i potrzebujesz innego wyjścia (VPN albo ręczne wrzucenie plików do `raw/`).

---

## Ręczna aktualizacja

```bash
cd rejestry-warszawa
./update.sh
```

Skrypt:

1. instaluje/aktualizuje `openpyxl` i `pdfplumber`,
2. uruchamia `python build.py --site-only` (Ursus + Praga-Północ),
3. czyści `__pycache__`,
4. `git add site/data/ursus site/data/praga-polnoc site/data/index.json`,
5. jeśli nic się nie zmieniło — kończy bez commita,
6. jeśli tak: commit `Aktualizacja Ursus i Praga-Północ RRRR-MM-DD` + push.

Push uruchamia workflow, który przebudowuje 16 dzielnic z GUNB
i publikuje całość. Strona jest aktualna po ~2 minutach.

### Tylko jedna dzielnica

```bash
./update.sh praga-polnoc
```

### Wszystko lokalnie (do testów, ~6 min)

```bash
python3 build.py
```

### Bez pobierania (z cache w `raw/`)

```bash
python3 build.py --site-only --offline
```

### Tylko przebudowa HTML

```bash
python3 build.py --render-only
```

---

## Automat co dwa tydzień

### Linux / macOS — cron

```bash
crontab -e
```

Dopisz (1. i 15. dnia miesiąca o 4:10):

```cron
10 4 1,15 * * cd /home/twoj_user/rejestry-warszawa && ./update.sh >> /var/log/rejestry.log 2>&1
```

### Linux — systemd timer (pewniejszy niż cron)

`/etc/systemd/system/rejestry.service`:

```ini
[Unit]
Description=Aktualizacja Ursus i Praga-Północ
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=twoj_user
WorkingDirectory=/home/twoj_user/rejestry-warszawa
ExecStart=/home/twoj_user/rejestry-warszawa/update.sh
TimeoutStartSec=1800
```

`/etc/systemd/system/rejestry.timer`:

```ini
[Unit]
Description=Aktualizacja rejestrów co dwa tygodnie

[Timer]
OnCalendar=*-*-1,15 04:10:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rejestry.timer
systemctl list-timers rejestry.timer
```

`Persistent=true` sprawia, że po włączeniu serwera zaległe zadanie
wykona się od razu.

### Windows — Harmonogram zadań

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\Program Files\Git\bin\bash.exe" `
           -Argument "-lc 'cd /c/Users/twoj_user/rejestry-warszawa && ./update.sh'" `
           -WorkingDirectory "C:\Users\twoj_user\rejestry-warszawa"
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 2 -DaysOfWeek Monday -At 4:10am
Register-ScheduledTask -TaskName "Rejestry Warszawa" -Action $action -Trigger $trigger
```

Wymaga Git for Windows (dostarcza `bash.exe`).

---

## Wariant: Vibe CLI na serwerze

Jeśli wolisz, żeby aktualizację prowadził agent:

1. Zainstaluj Vibe CLI na serwerze i otwórz je w katalogu repo:

   ```bash
   cd rejestry-warszawa
   vibe
   ```

2. Wklej zawartość **[PROMPT-aktualizacja.txt](PROMPT-aktualizacja.txt)**
   jako pierwszą wiadomość.

3. Agent sprawdzi dostęp do źródeł, uruchomi build, porówna liczby pozycji
   z poprzednim przebiegiem, zgłosi anomalie i zrobi commit + push.

4. Żeby chodziło cyklicznie:

   ```
   Ustaw to jako zadanie co dwa tygodnie, 1. i 15. o 4:10.
   ```

   Vibe CLI ma wbudowane narzędzie `cron` — sam zapisze harmonogram.

Zaleta względem `update.sh`: agent zauważy, gdy liczba pozycji w roczniku
**spadnie** (co zwykle znaczy, że urząd zmienił układ pliku i parser gubi
wiersze), i nie wypchnie zepsutych danych.

---

## Co robić, gdy coś padnie

### `403` przy pobieraniu

Maszyna jest blokowana albo brakuje nagłówka `Referer`. `parsers.download()`
wysyła `Referer: <adres dzielnicy>/` — CDN `cdn.um.warszawa.pl` bez tego
zwraca 403.

### Workflow pada na „Konfiguracja GitHub Pages”

Pages nie są włączone. Zobacz krok 1 wyżej.

### Liczba pozycji spadła

Najczęstsza przyczyna: urząd zmienił układ arkusza albo nazwy kolumn.
W logu szukaj:

* `- pominięto <rejestr> (brak pliku)`
* `! <plik>: inny dokument`
* `! parsowanie <plik>`

Diagnostyka pojedynczego pliku:

```bash
python3 -c "
import sys; sys.path.insert(0,'.')
import parsers
from districts import ursus
cfg=[c for c in ursus.REGISTERS if c['id']=='dec_wz'][0]
m=parsers.read_matrix('raw/ursus/rejestr_dec_wz_2026.pdf')
print('wierszy:',len(m))
print('naglowek:',parsers.find_header(m))
print('wynik:',len(parsers.parse_matrix(m,cfg)))
"
```

### Nowy rejestr na stronie dzielnicy

Dopisz wpis do `REGISTERS` w `districts/<dzielnica>.py`:

```python
dict(id='dec_zrid', name='Decyzje ZRID', short='ZRID',
     desc='...', match='rejestr_decyzji_zrid',
     pdf_title='rejestr decyzji zrid',
     cols=[('nr', 2, 'Nr decyzji', 'w-28'), ...],
     date=3),
```

* `match` — fragment nazwy pliku,
* `pdf_title` — fragment tytułu w treści PDF-a (chroni przed podmienionymi
  plikami; sprawdzany tylko dla PDF-ów),
* `cols` — numer kolumny w arkuszu (1-based) i szerokość.

### Nowa dzielnica z własną stroną

Skopiuj `districts/praga_polnoc.py`, popraw `BASE`, `PAGES`, `REGISTERS`,
`list_sources()` i `GUNB_ORGAN`. Potem w `build.py`:

```python
dict(slug='wola', name='Wola', organ='Prezydent Miasta Warszawa - Wola',
     site=wola),
```

Dzielnica z `site=` przestaje być budowana przez CI — musi ją budować
twoja maszyna (`--site-only`).

---

## Struktura repo

```
build.py                 generator (CLI)
gunb.py                  plik zbiorczy GUNB
parsers.py               XLSX/PDF → wiersze
districts/
  base.py                wspólna logika rocznika
  ursus.py               9 rejestrów Ursusa
  praga_polnoc.py        3 rejestry Pragi-Północ
templates/               index.html, style.css, app.js, logo
site/                    WYNIK — to trafia na GitHub Pages
raw/                     cache pobranych plików (poza repo)
update.sh                Ursus + Praga-Północ → commit → push
.github/workflows/
  update.yml             16 dzielnic z GUNB + publikacja
```
