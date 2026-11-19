# Rejestry Warszawa — konfiguracja serwera

Ten plik jest samodzielny. Zawiera wszystko, co trzeba zrobić na maszynie,
która ma aktualizować rejestry Ursusa i Pragi-Północ.

---

## Co robi serwer, a czego nie robi

Serwer buduje **tylko dwie dzielnice**:

| Dzielnica | Źródło | Rejestry |
|---|---|---|
| Ursus | `ursus.um.warszawa.pl/wykazy` | 9 (WZ, PnB, LCP, ZRID, wnioski, zgłoszenia, umowy art. 16) |
| Praga-Północ | `pragapn.um.warszawa.pl/-/ogloszenia-2` | 3 (WZ, ICP, wnioski WZ) |

Pozostałe **16 dzielnic** buduje GitHub Actions co poniedziałek z pliku
zbiorczego GUNB. Nie ruszaj ich — pełny build nadpisałby 41 MB danych
i zrobił ogromny diff.

Powód podziału: `*.um.warszawa.pl` zwraca serwerom GitHuba HTTP 403.
`wyszukiwarka.gunb.gov.pl` — nie.

```
serwer                    GitHub
──────                    ──────
Ursus + Praga-Północ  ──►  repo (site/data/ursus, site/data/praga-polnoc)
commit + push                    │
                                 ▼
                          GitHub Actions
                          16 dzielnic z GUNB
                                 │
                                 ▼
                          GitHub Pages
```

---

## Wymagania

* Python 3.10+
* `git` z zapisanymi danymi dostępowymi do `kadece/rejestry-warszawa`
* otwarta sieć do:
  * `ursus.um.warszawa.pl`
  * `pragapn.um.warszawa.pl`
  * `cdn.um.warszawa.pl` (tu leżą pliki — wymaga nagłówka `Referer`,
    skrypt sam go wysyła)
  * `github.com`

Sprawdzenie dostępu — **zrób to najpierw**:

```bash
curl -sI https://ursus.um.warszawa.pl/wykazy | head -1
curl -sI https://pragapn.um.warszawa.pl/-/ogloszenia-2 | head -1
```

Obie komendy muszą zwrócić `200`. Jeśli `403` — ta maszyna też jest
blokowana i potrzebujesz VPN albo innego wyjścia.

---

## Konfiguracja — krok po kroku

### 1. Klon repozytorium

```bash
git clone https://github.com/kadece/rejestry-warszawa.git
cd rejestry-warszawa
```

Jeśli git pyta o hasło, użyj tokenu osobistego jako hasła
(Settings → Developer settings → Personal access tokens → Fine-grained,
zakres: `Contents: Read and write` na tym repo).

### 2. Zależności

```bash
python3 -m pip install openpyxl pdfplumber
```

### 3. Uprawnienia do skryptu

```bash
chmod +x update.sh
```

### 4. Próba na jednej dzielnicy

```bash
./update.sh ursus
```

Oczekiwany wynik na końcu:

```
== gotowe — GitHub Pages opublikuje stronę w ciągu ~1 minuty ==
```

Jeśli zobaczysz `== brak zmian w danych — nic nie commituję ==`, to też
dobrze — znaczy, że dane są aktualne.

### 5. Pełna próba

```bash
./update.sh
```

Pierwsze uruchomienie pobiera ~9 MB PDF-ów i arkuszy Ursusa oraz ~150
plików Pragi-Północ, więc potrwa kilka minut. Kolejne będą szybkie, bo
`raw/` działa jak cache.

---

## Cron

### Wpis

```bash
crontab -e
```

Dopisz na końcu:

```cron
# Rejestry Warszawa — Ursus i Praga-Północ, 1. i 15. dnia miesiąca o 4:10
10 4 1,15 * * cd /home/twoj_user/rejestry-warszawa && ./update.sh >> /var/log/rejestry.log 2>&1
```

Zamień `/home/twoj_user/rejestry-warszawa` na swoją ścieżkę.

### Dlaczego `cd` w linii crona

Cron startuje w katalogu domowym. `update.sh` sam robi `cd` do swojego
katalogu, ale jawne `cd` chroni przed pomyłką, gdyby skrypt był wołany
inaczej.

### Dlaczego `>> /var/log/rejestry.log 2>&1`

Bez tego nie zobaczysz, co się stało. Cron wysyła output mailem, ale
na serwerze bez MTA przepada.

Log może rosnąć — jeśli chcesz go przyciąć, dodaj do `crontab`:

```cron
0 5 1 * * truncate -s 0 /var/log/rejestry.log
```

### Sprawdzenie, czy cron działa

```bash
# czy wpis jest
crontab -l

# czy coś się wykonało
tail -n 40 /var/log/rejestry.log

# czy cron w ogóle chodzi
systemctl status cron    # Debian/Ubuntu
systemctl status crond   # RHEL/Fedora
```

---

## Alternatywa: systemd timer

Pewniejszy niż cron — nadrabia zaległe zadania po restarcie i ma
porządne logi.

`/etc/systemd/system/rejestry.service`:

```ini
[Unit]
Description=Aktualizacja rejestrów Ursus i Praga-Północ
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

Ręczne uruchomienie i logi:

```bash
sudo systemctl start rejestry.service
journalctl -u rejestry.service -n 50
```

---

## Alternatywa: Windows

Wymaga Git for Windows (dostarcza `bash.exe`).

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\Program Files\Git\bin\bash.exe" `
           -Argument "-lc 'cd /c/Users/twoj_user/rejestry-warszawa && ./update.sh'" `
           -WorkingDirectory "C:\Users\twoj_user\rejestry-warszawa"
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 2 -DaysOfWeek Monday -At 4:10am
Register-ScheduledTask -TaskName "Rejestry Warszawa" -Action $action -Trigger $trigger
```

---

## Co dokładnie robi `update.sh`

```bash
python3 -m pip install --quiet --upgrade openpyxl pdfplumber   # zależności
python3 build.py --site-only                                   # Ursus + Praga-Północ
rm -rf __pycache__ districts/__pycache__                       # porządki
git add site/data/ursus site/data/praga-polnoc site/data/index.json
git diff --cached --quiet && exit 0                            # brak zmian → koniec
git commit -m "Aktualizacja Ursus i Praga-Północ RRRR-MM-DD"
git push
```

Push uruchamia workflow, który przebudowuje 16 dzielnic z GUNB
i publikuje całość na GitHub Pages. Strona jest aktualna po ~2 minutach.

---

## Weryfikacja po pierwszym uruchomieniu

1. **Czy dane się zmieniły**

   ```bash
   git log --oneline -3
   ```

2. **Czy workflow przeszedł**

   https://github.com/kadece/rejestry-warszawa/actions/workflows/update.yml

   Powinny być dwa zielone joby: `build` i `deploy`.

3. **Czy strona żyje**

   ```bash
   curl -sI https://kadece.github.io/rejestry-warszawa/ | head -1
   curl -sI https://kadece.github.io/rejestry-warszawa/data/index.json | head -1
   ```

   Obie muszą zwrócić `200`. Jeśli `data/index.json` daje `404`, to znaczy,
   że Pages są ustawione na „Deploy from a branch" zamiast
   „GitHub Actions" — popraw w Settings → Pages.

---

## Typowe problemy

### `403` przy pobieraniu

Maszyna jest blokowana albo brakuje nagłówka `Referer`. Skrypt wysyła
`Referer: <adres dzielnicy>/` sam — jeśli nadal 403, to blokada po IP.

### `Permission denied (publickey)` przy `git push`

Klucz SSH nie jest dodany do agenta albo nie ma go na GitHubie:

```bash
ssh -T git@github.com          # powinno przywitać po nazwie użytkownika
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

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

### `ModuleNotFoundError: pdfplumber`

Zależności zainstalowały się w innym interpreterze niż ten, którym
uruchamiasz skrypt. Wymuś konkretny:

```bash
PYTHON=/usr/bin/python3 ./update.sh
```

### Cron nic nie robi

* ścieżka w `crontab` musi być bezwzględna,
* cron ma minimalne `PATH` — dlatego `update.sh` używa `python3` z `PATH`,
  a nie zaszytej ścieżki; jeśli to problem, ustaw `PYTHON=` na początku
  linii crona:

  ```cron
  10 4 1,15 * * cd /home/twoj_user/rejestry-warszawa && PYTHON=/usr/bin/python3 ./update.sh >> /var/log/rejestry.log 2>&1
  ```

* sprawdź log — jeśli plik nie istnieje, cron w ogóle nie wystartował.

---

## Czego nie robić

* **Nie uruchamiaj `python3 build.py` bez `--site-only`** na serwerze —
  nadpisze 41 MB danych z GUNB i zrobi ogromny commit.
* **Nie commituj `raw/`** — to cache, jest w `.gitignore`.
* **Nie ruszaj repo `rejestry-ursus`** — to osobny, zamrożony projekt.

---

## Struktura repo

```
build.py                 generator (--gunb-only / --site-only / --district)
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
