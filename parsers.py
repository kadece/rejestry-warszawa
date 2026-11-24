# -*- coding: utf-8 -*-
"""Wspólna warstwa parsowania rejestrów dzielnicowych.

Każdy rejestr (XLSX albo PDF) sprowadzamy do macierzy wierszy, a potem do
listy pozycji `{'d': 'YYYY-MM-DD', 'c': {klucz: wartość}}`. Dzięki temu
format pliku nie ma znaczenia dla reszty projektu.

Układ arkuszy różni się między dzielnicami i rocznikami:
  * wiersz nagłówka bywa w wierszu 2, 4 albo 7,
  * nagłówek bywa dwuwierszowy („Nr decyzji i data jej wydania” + „nr | data”),
  * kolumna „Lp.” bywa w kolumnie A albo B,
  * kolejność kolumn zmienia się między latami.
Dlatego nagłówek znajdujemy po treści, a kolumny mapujemy po nazwach.
"""
import ssl
import datetime as dt
import os
import re
import urllib.parse
import urllib.request

import openpyxl

try:
    import pdfplumber
except ImportError:                                    # pragma: no cover
    pdfplumber = None

try:
    import xlrd                                       # stare rejestry .xls
except ImportError:                                    # pragma: no cover
    xlrd = None

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

MONTHS_PL = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
             'lipca', 'sierpnia', 'września', 'października', 'listopada',
             'grudnia']

MONTH_WORDS = {
    'styczen': 1, 'stycznia': 1, 'luty': 2, 'lutego': 2, 'marzec': 3,
    'marca': 3, 'kwiecien': 4, 'kwietnia': 4, 'maj': 5, 'maja': 5,
    'czerwiec': 6, 'czerwca': 6, 'lipiec': 7, 'lipca': 7, 'sierpien': 8,
    'sierpnia': 8, 'wrzesien': 9, 'wrzesnia': 9, 'pazdziernik': 10,
    'pazdziernika': 10, 'listopad': 11, 'listopada': 11, 'grudzien': 12,
    'grudnia': 12,
}

RE_DMY = re.compile(r'(\d{1,2})\s*[.\-/]\s*(\d{2,3})\s*[.\-/]\s*(\d{4})')
RE_YMD = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
RE_WORDS = re.compile(r'(\d{1,2})\s+([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)\s*(\d{4})')
RE_LP = re.compile(r'^l\s*\.?\s*p\s*\.?$', re.I)
RE_LP_VALUE = re.compile(r'^\d+\.?$')


# --------------------------------------------------------------------------
# Tekst
# --------------------------------------------------------------------------


def fold(s):
    """Usuwa polskie znaki diakrytyczne — do porównań tekstowych."""
    for a, b in (('ą', 'a'), ('ć', 'c'), ('ę', 'e'), ('ł', 'l'), ('ń', 'n'),
                 ('ó', 'o'), ('ś', 's'), ('ź', 'z'), ('ż', 'z')):
        s = s.replace(a, b)
    return s


def clean(v):
    if v is None:
        return ''
    # komórki-formaty daty muszą wyjść jako tekst, inaczej json.dump wywala
    # się na "Object of type datetime is not JSON serializable"
    if isinstance(v, dt.datetime):
        return '%02d.%02d.%04d' % (v.day, v.month, v.year)
    if isinstance(v, dt.date):
        return '%02d.%02d.%04d' % (v.day, v.month, v.year)
    s = str(v).replace('\xa0', ' ').replace('\u200b', '')
    return re.sub(r'[ \t\r\n]+', ' ', s).strip()


def parse_date(value):
    """Zwraca ISO 'YYYY-MM-DD' albo None."""
    if value is None or value == '':
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (int, float)) and 20000 < float(value) < 80000:
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(value))).isoformat()

    s = str(value)
    m = RE_YMD.search(s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return '%04d-%02d-%02d' % (y, mo, d)

    m = RE_DMY.search(s)
    if m:
        d, mo_raw, y = int(m.group(1)), m.group(2), int(m.group(3))
        mo = int(mo_raw)
        if mo > 12 and len(mo_raw) == 3:               # literówka "07.035.2026"
            mo = int(mo_raw[:2])
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return '%04d-%02d-%02d' % (y, mo, d)

    # literówka bez drugiej kropki: "14.062019"
    m = re.search(r'\b(\d{1,2})\.(\d{2})(\d{4})\b', s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return '%04d-%02d-%02d' % (y, mo, d)

    # bardzo tolerancyjny zapis: "15 .01 2020", "18.06,.2020"
    m = re.search(r'(\d{1,2})\s*[.,/\-]+\s*(\d{1,2})\s*[.,/\-]*\s*(\d{4})', s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return '%04d-%02d-%02d' % (y, mo, d)

    m = RE_WORDS.search(s)
    if m:
        d, word, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mo = MONTH_WORDS.get(fold(word))
        if mo and 1 <= d <= 31:
            return '%04d-%02d-%02d' % (y, mo, d)
    return None


def is_junk_row(cells):
    """Wiersze typu 'Kolumna 1 | Kolumna 2 | ...' albo puste."""
    joined = ' '.join(str(c) for c in cells if c)
    if not joined.strip():
        return True
    return bool(re.match(r'^(Kolumna\s*\d+\s*)+$', joined.strip(), re.I))


def is_numbering_row(vals):
    """Wiersz '1 | 2 | 3 | 4 | 5 | 6 | 7' pod nagłówkiem."""
    nums = [v for v in vals if v]
    if len(nums) < 3:
        return False
    return all(re.fullmatch(r'\d{1,2}\.?', v) for v in nums)


# --------------------------------------------------------------------------
# Macierz wierszy
# --------------------------------------------------------------------------


def read_matrix(path):
    """Czyta XLSX albo PDF i zwraca listę wierszy (lista stringów)."""
    if path.lower().endswith('.pdf'):
        return _read_pdf(path)
    return _read_xlsx(path)


def _read_xls(path):
    """Stare, jednoplatformowe .xls-y (xlrd)."""
    if xlrd is None:
        raise RuntimeError('brak xlrd — nie mogę czytać .xls')
    book = xlrd.open_workbook(path)
    ws = book.sheet_by_index(0)
    rows = []
    for r in range(ws.nrows):
        vals = []
        for c in range(ws.ncols):
            if ws.cell_type(r, c) == xlrd.XL_CELL_DATE:
                try:
                    d = xlrd.xldate_as_datetime(ws.cell_value(r, c),
                                                 book.datemode)
                    vals.append(d.strftime('%Y-%m-%d'))
                    continue
                except Exception:
                    pass
            v = ws.cell_value(r, c)
            if isinstance(v, float) and v == int(v):
                v = int(v)
            vals.append(clean(str(v) if v != '' else ''))
        rows.append(vals)
    book.release_resources()
    return rows


def _read_xlsx(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xls', '.xlt'):
        return _read_xls(path)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([clean(c) for c in row])
    wb.close()
    return rows


def _read_pdf(path):
    if pdfplumber is None:
        raise RuntimeError('brak pdfplumber — nie mogę czytać PDF')
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            for raw in table:
                rows.append([clean(c) for c in raw])
    return rows


def find_header(rows, hint=1):
    """Zwraca (indeks wiersza nagłówka, offset kolumny 'Lp.').

    Szuka po treści, bo urząd zmienia numer wiersza między rocznikami.
    Część plików nie ma wcale kolumny „Lp.” — wtedy szukamy wiersza,
    który wygląda na nagłówek tabeli (kilka etykiet i znane nazwy kolumn).
    """
    for r, row in enumerate(rows[:25]):
        for c, v in enumerate(row[:6]):
            if v and RE_LP.match(v.strip()):
                return r, c
    for r, row in enumerate(rows[:25]):
        vals = [fold((v or '').strip().lower()) for v in row[:8]]
        if sum(1 for v in vals if v) < 3:
            continue
        joined = ' | '.join(vals)
        if ('nr decyzji' in joined or 'znak sprawy' in joined
                or 'nr i data' in joined or 'numer i data' in joined
                or ('wniosek' in joined and 'data' in joined)):
            return r, 0
    return hint - 1, 0


def build_headers(rows, header_row, offset):
    """Scala nagłówek z ewentualnym drugim wierszem nagłówkowym.

    Przykład (Praga-Północ 2021):
        Lp. | Nr decyzji i data jej wydania | | Nazwa wnioskodawcy | ...
            | nr                          | data (rrrr-mm-dd) | ...
    Scalamy tylko, gdy w pierwszym wierszu są puste komórki (i drugi
    wiersz to nie dane) — w nagłówku jednowierszowym (mokotowskie
    „Nr decyzji i data jej wydania …”) niczego nie domyślamy się.
    """
    width = max(len(r) for r in rows[header_row:header_row + 2]) - offset
    width = max(width, 1)

    def slice_row(r):
        row = rows[r] if r < len(rows) else []
        return [(row[offset + i] if offset + i < len(row) else '')
                for i in range(width)]

    first = slice_row(header_row)
    merged = list(first)
    nxt = header_row + 1
    if nxt < len(rows) and any(not v for v in first):
        second = slice_row(nxt)
        if (not is_numbering_row(second)
                and not (second and RE_LP_VALUE.match(second[0] or ''))):
            for i, v in enumerate(second):
                if v:
                    merged[i] = (merged[i] + ' ' + v).strip() if merged[i] else v
            return [fold(h.lower()) for h in merged], nxt + 1
    return [fold(h.lower()) for h in merged], header_row + 1


def map_by_header(headers):
    """Role kolumn rozpoznawane po treści nagłówka."""
    m = {}
    for i, h in enumerate(headers):
        if not h:
            continue
        if ('data' in h and ('nr' in h or 'numer' in h or 'wplyw' in h
                             or 'wydania' in h)):
            # „Numer i data wpływu wniosku”, „Nr decyzji i data jej wydania” —
            # znak i data zlepione w jednej komórce (mokotowskie .xls 2018+)
            m.setdefault('nrdata', i)
        elif 'nr decyzji' in h or 'znak sprawy' in h or h == 'nr' \
                or h == 'wniosek':
            m.setdefault('nr', i)
        elif h.startswith('data') or h.endswith('data') or h == 'data':
            m.setdefault('data', i)
        elif 'wnioskodawc' in h:
            m.setdefault('wn', i)
        elif 'streszczenie' in h:
            m.setdefault('inw', i)
        elif ('nazwa inwestycji' in h or 'rodzaj inwestycji' in h
              or h == 'opis'):
            m.setdefault('inw', i)
        elif ('oznaczenie nieruchomosci' in h and 'ulica' in h) \
                or 'adres inwestycji' in h or h == 'ulica' \
                or 'teren inw' in h:
            m.setdefault('nier', i)
        elif ('oznaczenie nieruchomosci' in h and 'dz' in h) or 'obreb' in h:
            m.setdefault('dz', i)
        elif 'oznaczenie nieruchomosci' in h:
            m.setdefault('dz', i)                  # scalona komórka lokalizacji
        elif h.startswith('nr i data'):          # scalone „Nr i data decyzji”
            m.setdefault('nr', i)
    return m


def title_from_matrix(rows):
    """Tytuł dokumentu — pierwsza niepusta komórka w pierwszych trzech wierszach.

    Urząd publikuje czasem pod nazwą jednego rejestru plik innego (np. pod
    `rejestr_wnioskow_lcp_2019.pdf` leży rejestr zgłoszeń). Tytuł w treści
    pozwala to wychwycić.
    """
    for row in rows[:3]:
        for c in row:
            if c and c.strip():
                return clean(c)
    return ''


def parse_matrix(rows, cfg):
    """Macierz -> lista pozycji {'d': ISO, 'c': {klucz: wartość}}."""
    header_row, offset = find_header(rows, cfg.get('header', 1))
    headers, data_start = build_headers(rows, header_row, offset)

    if cfg.get('by_header'):
        colmap = map_by_header(headers)
        date_idx = colmap.get('data')
    else:
        colmap = {key: col - 1 - offset for key, col, _l, _w in cfg['cols']}
        date_idx = cfg['date'] - 1 - offset
    # „03.01.2018 1/WZ/MOK/2018” — data i znak zlepione w jednej komórce
    nd = colmap.pop('nrdata', None)

    out = []
    started = False
    # Niektóre PDF-y (np. mokotowskie rejestry decyzji) w ogóle nie mają
    # kolumny „Lp.” — wtedy akceptujemy każdy wiersz z treścią (śmieci
    # i numeracje kolumn odrzucamy jak zwykle).
    has_lp = bool(headers) and re.match(r'^l\s*\.?\s*p\s*\.?$', headers[0] or '', re.I)
    for row in rows[data_start:]:
        vals = [(row[offset + i] if offset + i < len(row) else '')
                for i in range(len(headers))]
        if is_junk_row(vals) or is_numbering_row(vals):
            continue

        # Arkusze mają numer w każdej kolumnie Lp. PDF-y natomiast scalają
        # tę komórkę — numer widnieje tylko w pierwszym wierszu, a kolejne
        # mają puste Lp. Dlatego po pierwszym numerowanym wierszu
        # akceptujemy też wiersze z pustym Lp. (o ile mają treść).
        if has_lp or not headers:
            if RE_LP_VALUE.match(vals[0] or ''):
                started = True
            elif not (started and not (vals[0] or '').strip()
                      and sum(1 for v in vals if v) >= 2):
                continue
        elif sum(1 for v in vals if v) < 2:
            continue

        cells = {}
        for key, idx in colmap.items():
            v = vals[idx] if idx < len(vals) else ''
            cells[key] = v.strip(' ,;')

        # wiersze-szkielety: urząd numeruje wiersz i wpisuje nazwę organu,
        # a resztę zostawia pustą
        if sum(1 for v in cells.values() if v) < 2:
            continue

        iso = None
        nr_date = None
        if nd is not None and nd < len(vals):
            raw = vals[nd]
            dm = RE_DMY.search(raw) or RE_YMD.search(raw)
            if dm:
                nr_date = dm.group(0)
                nr = (raw[:dm.start()] + raw[dm.end():]).strip(' ,;.-')
                if raw != nr and not cells.get('nr'):
                    cells['nr'] = nr
            elif raw and not cells.get('nr'):
                cells['nr'] = raw
        if date_idx is not None and date_idx < len(vals):
            iso = parse_date(vals[date_idx])
        if iso is None and nr_date:
            iso = parse_date(nr_date)
        if iso and not (2000 <= int(iso[:4]) <= 2100):
            iso = None                    # numeracja kolumn albo literówka urzędu

        out.append({'d': iso, 'c': cells})

    # od najnowszej; wpisy bez daty na końcu ('' jest najmniejszym stringiem,
    # więc przy reverse=True ląduje na końcu)
    out.sort(key=lambda x: x['d'] or '', reverse=True)
    return out


# --------------------------------------------------------------------------
# Sieć
# --------------------------------------------------------------------------


def ssl_context(verify_ssl=True):
    """Kontekst SSL domyślnie weryfikujący; z flagą — bez weryfikacji."""
    if verify_ssl:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(url, referer, timeout=90, verify_ssl=True):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        # CDN m.st. Warszawy odrzuca żądania bez Referer (HTTP 403)
        'Referer': referer,
    })
    with urllib.request.urlopen(req, timeout=timeout,
                                context=ssl_context(verify_ssl)) as r:
        return r.read()


def download(url, dest, referer, verify_ssl=True):
    data = fetch(url, referer, timeout=180, verify_ssl=verify_ssl)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'wb') as f:
        f.write(data)
    return len(data)


def safe_name(name, limit=70):
    return re.sub(r'[^A-Za-z0-9._-]', '_', urllib.parse.unquote(name))[:limit]


# --------------------------------------------------------------------------
# JSON w HTML
# --------------------------------------------------------------------------


def wrap_json(s):
    """Wstawia znak nowej linii po każdym `}` i `]` poza literałem tekstowym.

    Bez tego cała paczka danych ląduje w jednej linii pliku HTML: git nie
    potrafi pokazać sensownego diffu, a narzędzia czytające plik po liniach
    gubią zawartość. Nowe linie są wewnątrz JSON-a, więc dla przeglądarki
    nic się nie zmienia.
    """
    out = []
    in_str = False
    esc = False
    for ch in s:
        out.append(ch)
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in '}]':
            out.append('\n')
    return ''.join(out)
