# -*- coding: utf-8 -*-
"""Wspólna logika budowy rocznika — identyczna dla każdej dzielnicy.

Dzielnica dostarcza tylko:
  * metadane (slug, nazwa, adresy),
  * konfigurację rejestrów (jak rozpoznać plik, jak nazwać kolumny),
  * `list_sources(year)` — listę załączników dla rocznika.

Reszta (pobieranie, parsowanie, składanie JSON-a) jest tutaj.
"""
import datetime as dt
import hashlib
import html
import os
import re
import urllib.parse

import parsers


MONTH_ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
               'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12}


def month_from_name(name, year):
    """Numer miesiąca (1-12) wyciągnięty z nazwy pliku; 0 gdy brak/roczny.

    Urzędy nie są konsekwentne: «10_2026», « 9_2025», «12-2022»,
    „_VIII_2025”, „luty_2026”, „czerwiec-2026” — łapiemy wszystko.
    """
    low = parsers.fold(name.lower())
    m = re.search(r'[^\d](\d{1,2})\s*[-_, ]{0,3}%d(?!\d)' % year, name)
    if m:
        v = int(m.group(1))
        if 1 <= v <= 12:
            return v
    m = re.search(r'[_ ]((?:xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i))'
                  r'[_ ]*%d(?!\d)' % year, low)
    if m and m.group(1) in MONTH_ROMAN:
        return MONTH_ROMAN[m.group(1)]
    for w, mo in parsers.MONTH_WORDS.items():
        if re.search(r'[^a-z]%s[^a-z]{0,3}%d(?!\d)' % (w, year), low):
            return mo
    # układ odwrotny: rok przed miesiącem — „2020__MARZEC”, „2020_09”
    m = re.search(r'%d\s*[-_, ]{0,3}(\d{1,2})(?!\d)' % year, name)
    if m:
        v = int(m.group(1))
        if 1 <= v <= 12:
            return v
    m = re.search(r'%d[^a-z0-9]{0,3}'
                  r'((?:xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i))(?![a-z])'
                  % year, low)
    if m and m.group(1) in MONTH_ROMAN:
        return MONTH_ROMAN[m.group(1)]
    for w, mo in parsers.MONTH_WORDS.items():
        if re.search(r'%d[^a-z0-9]{0,3}%s\b' % (year, w), low):
            return mo
    return 0


def year_from_name(name):
    """Rok z nazwy pliku albo None."""
    m = re.search(r'(20\d{2})', name)
    return int(m.group(1)) if m else None


def fetch_page(url, cache, referer, offline=False, verify_ssl=True):
    """Pobiera stronę (albo czyta ją z cache) i zwraca HTML."""
    if offline:
        if not os.path.exists(cache):
            raise RuntimeError('brak pliku %s' % os.path.basename(cache))
        with open(cache, encoding='utf-8', errors='replace') as f:
            return f.read()
    content = parsers.fetch(url, referer, verify_ssl=verify_ssl).decode('utf-8', 'replace')
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, 'w', encoding='utf-8') as f:
        f.write(content)
    return content


_DOC_LINK = re.compile(
    r'href="((?:https?://cdn\.um\.warszawa\.pl)?/documents/[^"]+)"', re.I)


def um_documents(content):
    """Załączniki /documents/ z CMS stron um.warszawa.pl.

    Link ma postać /documents/<id>/<id>/<nazwa+pliku>.xlsx/<uuid>?t=...
    (czasem z pełną domeną cdn.um.warszawa.pl). Nazwa pliku wychodzi
    z przedostatniego segmentu URL (plusy kodują spacje).
    Zwraca listę {'name', 'url'}.
    """
    out = []
    for m in _DOC_LINK.finditer(content):
        url = m.group(1)
        seg = url.split('?')[0].rstrip('/').split('/')
        raw = seg[-2] if len(seg) > 2 else seg[-1]
        name = html.unescape(urllib.parse.unquote(raw)).replace('+', ' ')
        if not re.search(r'\.(xlsx|xls|pdf)$', name, re.I):
            continue
        out.append({'name': name,
                    'url': 'https://cdn.um.warszawa.pl' + url
                           if url.startswith('/') else url})
    return out


def att_file(att, kind, year, month=0, limit=50):
    """Nazwa pliku cache dla załącznika — deterministyczna i unikalna.

    Skrót URL w nazwie rozdziela dwa arkusze o tej samej nazwie
    (urząd bywa wgrany poprawkę albo dwa rejestry pod jednym tytułem)
    — dzięki temu cache w raw/ po pobraniu offline daje te same dane.
    """
    stem, ext = os.path.splitext(att['name'])
    h = hashlib.md5(att['url'].encode('utf-8')).hexdigest()[:6]
    return '%s_%04d_%02d_%s_%s%s' % (kind, year, month,
                                     parsers.safe_name(stem, limit), h, ext)


def build_year(dist, year, raw_dir, offline=False):
    """Zwraca dict z danymi jednego rocznika jednej dzielnicy."""
    os.makedirs(raw_dir, exist_ok=True)

    atts = []
    source_url = dist.page_url(year)
    try:
        atts, source_url = dist.list_sources(year, raw_dir, offline=offline)
        print('  znaleziono %d załączników' % len(atts))
    except Exception as e:
        print('  ! nie udało się pobrać listy: %s' % e)
        print('  -> korzystam z plików w raw/')

    registers = []
    for cfg in dist.REGISTERS:
        # Rejestr może być w jednym pliku (Ursus) albo w kilkunastu plikach
        # miesięcznych (Praga-Północ) — bierzemy wszystkie pasujące.
        found = [a for a in atts if dist.matches(cfg, a['file'])]

        if not found:
            # szukamy w cache — tylko pliki z właściwego rocznika
            cand = [f for f in os.listdir(raw_dir)
                    if dist.matches(cfg, f)
                    and f.lower().endswith(('.xlsx', '.pdf'))
                    and str(year) in f]
            if not cand:
                print('  - pominięto %s (brak pliku)' % cfg['id'])
                continue
            found = [{'file': f, 'url': ''} for f in sorted(cand)]

        rows = []
        used = []
        for att in found:
            dest = os.path.join(raw_dir, att['file'])
            if offline:
                if not os.path.exists(dest):
                    print('  - pominięto %s (brak w cache)' % att['file'])
                    continue
            else:
                try:
                    size = parsers.download(att['url'], dest, dist.BASE + '/')
                    print('  + %-46s %7d B' % (att['file'], size))
                except Exception as e:
                    print('  ! pobieranie %s: %s' % (att['file'], e))
                    if not os.path.exists(dest):
                        continue

            try:
                matrix = parsers.read_matrix(dest)
            except Exception as e:
                print('  ! odczyt %s: %s' % (att['file'], e))
                continue

            # Pod nazwą jednego rejestru bywa opublikowany inny dokument
            # (Ursus 2019: rejestr zgłoszeń pod nazwą wniosków LCP).
            # Sprawdzamy tylko PDF-y — arkusze mają własne tytuły.
            want = cfg.get('pdf_title')
            if want and dest.lower().endswith('.pdf'):
                got = parsers.fold(parsers.title_from_matrix(matrix).lower())
                if want not in got:
                    print('    ! %s: inny dokument (%r) — pomijam'
                          % (att['file'], got))
                    continue

            try:
                part = parsers.parse_matrix(matrix, cfg)
            except Exception as e:
                print('  ! parsowanie %s: %s' % (att['file'], e))
                continue

            # Plik łączony (WZ i CP w jednym) — wiersze rozdzielamy po
            # treści znaku sprawy, np. „86/WZ/MOK/2022” vs „25/CP/MOK/2022”.
            flt = att.get('nr_filter')
            if flt:
                before = len(part)
                part = [r for r in part
                        if re.search(flt, r['c'].get('nr') or '', re.I)]
                if before != len(part):
                    print('    ~ %-44s filtr %-6s: %d -> %d'
                          % (att['file'][:44], flt, before, len(part)))
            if cfg.get('by_date_year'):
                # rejestr skumulowany (kilka lat w jednym pliku) — kroimy
                # wiersze po dacie z wiersza, nie po nazwie pliku
                part = [r for r in part
                        if r['d'] and r['d'][:4] == str(year)]
            if part:
                rows.extend(part)
                used.append(att['file'])

        if not rows:
            print('  - pominięto %s (brak pozycji)' % cfg['id'])
            continue

        # od najnowszej; wpisy bez daty na końcu
        rows.sort(key=lambda x: x['d'] or '', reverse=True)
        no_date = sum(1 for r in rows if not r['d'])
        print('    -> %3d pozycji z %d plik(ów)%s'
              % (len(rows), len(used),
                 ' (%d bez daty)' % no_date if no_date else ''))

        registers.append({
            'id': cfg['id'],
            'name': cfg['name'],
            'short': cfg['short'],
            'desc': cfg['desc'],
            'file': (used[0] if len(used) == 1
                     else '%d plików miesięcznych' % len(used)),
            'url': found[0]['url'] if len(found) == 1 else dist.page_url(year),
            'cols': [{'k': k, 'l': l, 'w': w} for k, _c, l, w in cfg['cols']],
            'rows': rows,
        })

    total = sum(len(r['rows']) for r in registers)
    return {
        'district': dist.SLUG,
        'year': year,
        'source': source_url,
        'generated': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'total': total,
        'registers': registers,
    }
