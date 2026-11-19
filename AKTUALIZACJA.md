# Aktualizacja rejestrów — instrukcja dla serwera lokalnego

Ten dokument opisuje, jak uruchomić odświeżanie danych **na własnej
maszynie** i jak zautomatyzować je tak, żeby chodziło co dwa tygodnie.

---

## Dlaczego nie GitHub Actions

Sprawdzone: serwery GitHuba dostają **HTTP 403** od `*.um.warszawa.pl`.
Strony dzielnic blokują adresy z centrów danych. GUNB (`gunb.gov.pl`)
działa z GitHuba bez problemu, ale Ursus i Praga-Północ — nie.

Dlatego podział ról jest taki:

```
twoja maszyna                    GitHub
─────────────                    ──────
pobiera dane      ──push──►      repo (site/)
parsuje                            │
zapisuje JSON                      ▼
                            GitHub Actions
                            (tylko publikacja)
                                   │
                                   ▼
                            GitHub Pages
```

Workflow `.github/workflows/update.yml` **nie pobiera niczego** — bierze
katalog `site/` z repo i wrzuca go na Pages. Cała robota (pobieranie,
parsowanie) dzieje się u ciebie.

---

## Czego potrzebujesz

* Python 3.10 lub nowszy,
* `git` skonfigurowany z dostępem do `kadece/rejestry-warszawa`
  (klucz SSH albo token w `~/.git-credentials`),
* dostęp sieciowy do:
  * `wyszukiwarka.gunb.gov.pl` (plik zbiorczy, ~47 MB),
  * `ursus.um.warszawa.pl` i `cdn.um.warszawa.pl`,
  * `pragapn.um.warszawa.pl` i `cdn.um.warszawa.pl`.

Sprawdzenie dostępu:

```bash
curl -sI https://wyszukiwarka.gunb.gov.pl/pliki_pobranie/wynik_mazowieckie.zip | head -1
curl -sI https://ursus.um.warszawa.pl/wykazy | head -1
curl -sI https://pragapn.um.warszawa.pl/-/ogloszenia-2 | head -1
```

Wszystkie trzy powinny zwrócić `200`. Jeśli któraś zwróci `403` — ta
maszyna też jest blokowana i trzeba innego wyjścia (np. VPN albo ręczne
pobranie plików do `raw/`).

---

## Jednorazowa konfiguracja

```bash
# 1. Klon repo
git clone https://github.com/kadece/rejestry-warszawa.git
cd rejestry-warszawa

# 2. Zależności
python3 -m pip install openpyxl pdfplumber

# 3. Uprawnienia do skryptu
chmod +x update.sh

# 4. Próba na jednej dzielnicy (szybko, ~1 min)
./update.sh ursus
```

Jeśli `./update.sh ursus` przejdzie bez błędu i wypisze
`== gotowe ==`, konfiguracja jest skończona.

Pierwsze pełne uruchomienie potrwa **~6 minut** — GUNB to 47 MB do
pobrania i 334 MB CSV do przeczytania, a Ursus ma 56 PDF-ów i arkuszy.
Kolejne będą szybsze, bo `raw/` działa jak cache.

---

## Ręczna aktualizacja

```bash
cd rejestry-warszawa
./update.sh
```

Skrypt robi po kolei:

1. instaluje/aktualizuje `openpyxl` i `pdfplumber`,
2. uruchamia `python build.py` (wszystkie 18 dzielnic),
3. czyści `__pycache__`,
4. sprawdza, czy `site/` się zmieniło — jeśli nie, **kończy bez commita**,
5. jeśli tak: `git add site/`, commit `Aktualizacja rejestrów RRRR-MM-DD`,
   `git push`.

Po pushu GitHub Actions publikuje stronę w ciągu ~1 minuty.

### Tylko jedna dzielnica

```bash
./update.sh praga-polnoc
```

### Bez pobierania (z cache)

```bash
python3 build.py --offline
```

### Tylko przebudowa HTML

```bash
python3 build.py --render-only
```

---

## Automat co dwa tygodnie

### Linux / macOS — cron

```bash
crontab -e
```

Dopisz (1. i 15. dnia miesiąca o 4:10):

```cron
10 4 1,15 * * cd /home/twoj_user/rejestry-warszawa && ./update.sh >> /var/log/rejestry.log 2>&1
```

Sprawdzenie:

```bash
tail -f /var/log/rejestry.log
```

### Linux — systemd timer (pewniejszy niż cron)

`/etc/systemd/system/rejestry.service`:

```ini
[Unit]
Description=Aktualizacja rejestrów dzielnic Warszawy
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

`Persistent=true` oznacza, że jeśli serwer był wyłączony w zaplanowanym
terminie, zadanie wykona się po najbliższym włączeniu.

### Windows — Harmonogram zadań

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\Program Files\Git\bin\bash.exe" `
           -Argument "-lc 'cd /c/Users/twoj_user/rejestry-warszawa && ./update.sh'" `
           -WorkingDirectory "C:\Users\twoj_user\rejestry-warszawa"
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 2 -DaysOfWeek Monday -At 4:10am
Register-ScheduledTask -TaskName "Rejestry Warszawa" -Action $action -Trigger $trigger `
           -Description "Odświeżanie rejestrów dzielnic Warszawy"
```

Wymaga Git for Windows (dostarcza `bash.exe`).

---

## Wariant: Vibe CLI na serwerze

Jeśli wolisz, żeby aktualizację prowadził agent, a nie goły skrypt:

1. Zainstaluj Vibe CLI na serwerze i otwórz je w katalogu repo:

   ```bash
   cd rejestry-warszawa
   vibe
   ```

2. Wklej zawartość pliku **[PROMPT-aktualizacja.txt](PROMPT-aktualizacja.txt)**
   jako pierwszą wiadomość.

3. Agent sprawdzi dostęp do źródeł, uruchomi build, porówna liczby pozycji
   z poprzednim przebiegiem, zgłosi anomalie i zrobi commit + push.

4. Żeby chodziło cyklicznie, poproś agenta o zadanie cron:

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

### Liczba pozycji spadła

Najczęstsza przyczyna: urząd zmienił układ arkusza albo nazwy kolumn.
Sprawdź log — parser wypisuje `- pominięto <rejestr> (brak pliku)`
i `! <plik>: inny dokument`.

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

`match` to fragment nazwy pliku, `pdf_title` — fragment tytułu w treści
PDF-a (zabezpieczenie przed podmienionymi plikami), `cols` — numer kolumny
w arkuszu (1-based) i szerokość.

### Nowa dzielnica z własną stroną

Skopiuj `districts/praga_polnoc.py`, popraw `BASE`, `PAGES`, `REGISTERS`,
`list_sources()` i `GUNB_ORGAN`. Potem w `build.py`:

```python
dict(slug='wola', name='Wola', organ='Prezydent Miasta Warszawa - Wola',
     site=wola),
```

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
update.sh                pobierz → sparsuj → commit → push
.github/workflows/
  update.yml             publikacja site/ na Pages
```
