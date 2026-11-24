# -*- coding: utf-8 -*-
"""Pozwolenia na budowę dla całej Warszawy — oficjalne pliki GUNB.

Wyszukiwarka https://wyszukiwarka.gunb.gov.pl/ jest chroniona CAPTCHA, więc
nie nadaje się do automatyzacji. GUNB udostępnia jednak ten sam rejestr jako
pliki zbiorcze per województwo, aktualizowane co noc:

    https://wyszukiwarka.gunb.gov.pl/pliki_pobranie/wynik_mazowieckie.zip

Jeden plik CSV (~334 MB po rozpakowaniu, 31 kolumn, separator `;`, UTF-8 z BOM)
zawiera wszystkie organy Mazowsza od 2016 r. Dzielnicę rozpoznajemy po
kolumnie `nazwa_organu`, np. „Prezydent Miasta Warszawa - Ursus”.

Z jednego wiersza robimy dwie pozycje:
  * `wn_pnb`  — wniosek o pozwolenie (data wpływu),
  * `dec_pnb` — wydana decyzja (data wydania), tylko gdy data istnieje.
"""
import csv
import io
import os
import time
import zipfile

import parsers

URL = 'https://wyszukiwarka.gunb.gov.pl/pliki_pobranie/wynik_mazowieckie.zip'
ZIP_NAME = 'wynik_mazowieckie.zip'

# kolumny źródłowe, których używamy
C_ORGAN = 'nazwa_organu'
C_NR = 'numer_urzad'
C_WPLYW = 'data_wplywu_wniosku'
C_DEC_NR = 'numer_decyzji_urzedu'
C_DEC_DATA = 'data_wydania_decyzji'
C_INWESTOR = 'nazwa_inwestor'
C_ULICA = 'ulica'
C_ULICA2 = 'ulica_dalej'
C_NR_DOMU = 'nr_domu'
C_RODZAJ = 'rodzaj_inwestycji'
C_ZAM = 'nazwa_zam_budowlanego'
C_ZAM2 = 'nazwa_zamierzenia_bud'
C_JEDN = 'jednosta_numer_ew'
C_OBREB = 'obreb_numer'
C_DZIALKA = 'numer_dzialki'

COLS_WN = [('nr', 'Numer wniosku', 'nr'),
           ('inw', 'Zamierzenie budowlane', 'wide'),
           ('wn', 'Inwestor', 'mid'),
           ('nier', 'Lokalizacja', 'mid'),
           ('dz', 'Działka / obręb', ''),
           ('rodz', 'Rodzaj inwestycji', '')]

COLS_DEC = [('nr', 'Numer decyzji', 'nr'),
            ('inw', 'Zamierzenie budowlane', 'wide'),
            ('wn', 'Inwestor', 'mid'),
            ('nier', 'Lokalizacja', 'mid'),
            ('dz', 'Działka / obręb', ''),
            ('rodz', 'Rodzaj inwestycji', '')]


def download(raw_dir, offline=False, max_age_h=20):
    """Pobiera plik zbiorczy i zwraca ścieżkę do ZIP-a.

    GUNB publikuje nową paczkę co noc. Przy powtórnych buildach tego
    samego dnia nie ma sensu ściągać ~47 MB ponownie — zip młodszy
    niż `max_age_h` godzin jest brany z cache (na runnerze CI cache
    i tak jest zawsze zimny, więc niczego nie psuje).
    """
    os.makedirs(raw_dir, exist_ok=True)
    dest = os.path.join(raw_dir, ZIP_NAME)
    if os.path.exists(dest):
        if offline:
            return dest
        age_h = (time.time() - os.path.getmtime(dest)) / 3600.0
        if age_h < max_age_h:
            print('  = %-46s (cache %4.1f h)' % (ZIP_NAME, age_h))
            return dest
    elif offline:
        raise RuntimeError('brak pliku %s' % ZIP_NAME)
    # wyszukiwarka.gunb.gov.pl serwuje łańcuch certyfikatów, który nie
    # przechodzi weryfikacji („self-signed certificate in chain”), więc
    # weryfikację pomijamy — to publiczny plik zbiorczy, odstępstwa widać
    # po rozmiarze i liczbie pozycji.
    size = parsers.download(URL, dest, 'https://wyszukiwarka.gunb.gov.pl/',
                           verify_ssl=False)
    print('  + %-46s %7d B' % (ZIP_NAME, size))
    return dest


def _join(*parts):
    return ' '.join(p.strip() for p in parts if p and p.strip())


def read_all(zip_path, organs):
    """Jedno przejście przez plik — zwraca {organ: [wiersze]}.

    Plik ma ~334 MB po rozpakowaniu, więc czytamy go raz i rozdzielamy do
    kubełków. Osobne przejście na każdą dzielnicę trwałoby kilkanaście minut.
    """
    wanted = set(organs)
    out = {o: [] for o in organs}
    with zipfile.ZipFile(zip_path) as z:
        name = z.namelist()[0]
        with z.open(name) as raw:
            f = io.TextIOWrapper(raw, encoding='utf-8-sig', newline='')
            r = csv.reader(f, delimiter=';')
            hdr = next(r)
            idx = {h: i for i, h in enumerate(hdr)}

            def get(row, key):
                i = idx.get(key)
                if i is None or i >= len(row):
                    return ''
                return row[i].strip()

            for row in r:
                organ = get(row, C_ORGAN)
                if organ not in wanted:
                    continue
                lokal = _join(get(row, C_ULICA), get(row, C_NR_DOMU))
                if get(row, C_ULICA2):
                    lokal = _join(lokal, '/', get(row, C_ULICA2))
                dzialka = _join(get(row, C_JEDN), get(row, C_OBREB),
                                get(row, C_DZIALKA))
                cells = {
                    'inw': _join(get(row, C_ZAM), get(row, C_ZAM2)),
                    'wn': get(row, C_INWESTOR),
                    'nier': lokal,
                    'dz': dzialka,
                    'rodz': get(row, C_RODZAJ),
                }
                out[organ].append({
                    'wplyw': parsers.parse_date(get(row, C_WPLYW)),
                    'dec_data': parsers.parse_date(get(row, C_DEC_DATA)),
                    'nr_wn': get(row, C_NR),
                    'nr_dec': get(row, C_DEC_NR),
                    'cells': cells,
                })
    return out


def registers_for_year(rows, year):
    """Buduje dwa rejestry (wnioski, decyzje) dla jednego rocznika."""
    wn, dec = [], []
    for r in rows:
        if r['wplyw'] and r['wplyw'][:4] == str(year):
            c = dict(r['cells'])
            c['nr'] = r['nr_wn']
            wn.append({'d': r['wplyw'], 'c': c})
        if r['dec_data'] and r['dec_data'][:4] == str(year):
            c = dict(r['cells'])
            c['nr'] = r['nr_dec'] or r['nr_wn']
            dec.append({'d': r['dec_data'], 'c': c})

    def sort(rs):
        # od najnowszej; wpisy bez daty na końcu
        rs.sort(key=lambda x: x['d'] or '', reverse=True)
        return rs

    out = []
    if wn:
        out.append({
            'id': 'wn_pnb',
            'name': 'Wnioski o pozwolenie na budowę',
            'short': 'Wnioski PnB',
            'desc': 'Wnioski o pozwolenie na budowę złożone do organu '
                    'architektoniczno-budowlanego dzielnicy (rejestr GUNB).',
            'file': 'GUNB — wynik_mazowieckie.zip',
            'url': URL,
            'cols': [{'k': k, 'l': l, 'w': w} for k, l, w in COLS_WN],
            'rows': sort(wn),
        })
    if dec:
        out.append({
            'id': 'dec_pnb',
            'name': 'Decyzje o pozwoleniu na budowę',
            'short': 'Decyzje PnB',
            'desc': 'Decyzje o pozwoleniu na budowę wydane przez organ '
                    'architektoniczno-budowlany dzielnicy (rejestr GUNB).',
            'file': 'GUNB — wynik_mazowieckie.zip',
            'url': URL,
            'cols': [{'k': k, 'l': l, 'w': w} for k, l, w in COLS_DEC],
            'rows': sort(dec),
        })
    return out
