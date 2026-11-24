# -*- coding: utf-8 -*-
"""Dzielnica Mokotów — rejestry WZ i ICP.

Źródła (CMS um.warszawa.pl):
  * strona bieżąca  — wykazy-i-informacje-o-decyzjach (rocznik 2026),
  * archiwum wniosków i archiwum decyzji (2018–2025). Raz na sezon
    urząd zmienia styl nazw plików („WZIZT_03_2020.xls”,
    „wnioski wz maj 2025.pdf”, „decyzje_WZ_X_2025v2.pdf”) — nazwy
    rozpoznajemy po treści, a miesiąc po miesiącu w nazwie
    (patrz base.month_from_name).

Rejestry: wnioski i decyzje osobno dla WZ oraz ICP (cztery kolumny
rejestrów dzielonych wg znaku sprawy „12/WZ/MOK/2023” / „25/CP/MOK/2022”).
Część plików miesięcznych ma oba rodzaje w jednym dokumencie
(nawet gdy nazwa mówi tylko „wydane_wnioski_12-2022.pdf”) — te rozdzielamy
per wiersz filtrem po znaku sprawy (att['nr_filter']).

Znana literówka urzędu: „rejestr decyzji WZ_07_2027.pdf” to lipiec 2026.
Plik ma rok 2027 w nazwie, więc go pomijamy (dane lipca 2026 WZ,
braki w rejestrze decyzji WZ odnotowujemy w README).
"""
import os
import re

import parsers
from districts import base

SLUG = 'mokotow'
NAME = 'Mokotów'
SHORT = 'Mokotów'
BASE = 'https://mokotow.um.warszawa.pl'
PAGES = [
    BASE + '/wykazy-i-informacje-o-decyzjach',
    BASE + '/-/archiwum-informacje-o-wnioskach-o-wydanie-decyzji-o-'
           'warunkach-zabudowy-i-zagospodarowania-terenu',
    BASE + '/-/archiwum-informacje-o-wydanych-decyzjach-o-warunkach-'
           'zabudowy-i-zagospodarowania-terenu',
]
YEARS = list(range(2018, 2027))

# wn = wnioski (wszczęte postępowania), dec = decyzje wydane
_WN_COLS = [('nr', 0, 'Znak sprawy', 'nr'),
            ('inw', 0, 'Nazwa inwestycji z wniosku', 'wide'),
            ('wn', 0, 'Wnioskodawca', 'mid'),
            ('nier', 0, 'Adres inwestycji', 'mid'),
            ('dz', 0, 'Działka / obręb', '')]
_DEC_COLS = [('nr', 0, 'Nr decyzji', 'nr'),
             ('inw', 0, 'Streszczenie ustaleń', 'wide'),
             ('wn', 0, 'Wnioskodawca', 'mid'),
             ('nier', 0, 'Ulica', 'mid'),
             ('dz', 0, 'Obręb / działka', '')]

REGISTERS = [
    dict(
        id='wn_wz', match='wn_wz',
        name='Wszczęte postępowania — warunki zabudowy',
        short='Wnioski WZ',
        desc='Informacja o wnioskach o wydanie decyzji o warunkach '
             'zabudowy i zagospodarowania terenu.',
        header=1, date=None, by_header=True, cols=_WN_COLS,
    ),
    dict(
        id='wn_cp', match='wn_cp',
        name='Wszczęte postępowania — inwestycje celu publicznego',
        short='Wnioski ICP',
        desc='Informacja o wnioskach o ustalenie lokalizacji inwestycji '
             'celu publicznego.',
        header=1, date=None, by_header=True, cols=_WN_COLS,
    ),
    dict(
        id='dec_wz', match='dec_wz',
        name='Decyzje o warunkach zabudowy',
        short='Decyzje WZ',
        desc='Informacja o wydanych decyzjach w sprawie warunków '
             'zabudowy i zagospodarowania terenu.',
        header=2, date=None, by_header=True, cols=_DEC_COLS,
    ),
    dict(
        id='dec_cp', match='dec_cp',
        name='Decyzje o lokalizacji inwestycji celu publicznego',
        short='Decyzje ICP',
        desc='Informacja o wydanych decyzjach o ustaleniu lokalizacji '
             'inwestycji celu publicznego.',
        header=2, date=None, by_header=True, cols=_DEC_COLS,
    ),
]


def page_url(year):
    return PAGES[0]


def classify(text):
    """[(rodzaj rejestru, filtr znaku sprawy)] dla nazwy pliku."""
    t = parsers.fold(text.lower())
    # najpierw wnioski — tytuły typu „rejestr wniosków o wydanie
    # decyzji o warunkach zabudowy” zawierają też słowo „decyzji”
    if 'wniosk' in t:
        pref = 'wn'
    elif 'decyzj' in t:
        pref = 'dec'
    else:
        return []
    wz = bool(re.search(r'(^|[^a-z0-9])wz|wzizt|warunk|zabudow', t))
    cp = bool(re.search(r'licp|cel[a-z]*\-?\s*publiczn|lokalizacj'
                        r'|(?:^|[^a-z0-9])cp(?:$|[^a-z0-9])', t))
    if wz and cp:
        return [(pref + '_wz', r'\bwz\b'), (pref + '_cp', r'\bcp\b')]
    if wz:
        return [(pref + '_wz', None)]
    if cp:
        return [(pref + '_cp', None)]
    # nazwa nie mówi nic („wydane_wnioski_12-2022.pdf”) — pliki tego
    # typu okazały się mieszane WZ+CP, więc rozdzielamy po znaku sprawy
    return [(pref + '_wz', r'\bwz\b'), (pref + '_cp', r'\bcp\b')]


def matches(cfg, fname):
    return cfg['match'] in fname.lower()


def list_sources(year, raw_dir, offline=False):
    """Załączniki jednego rocznika ze wszystkich trzech stron."""
    out, seen = [], set()
    for i, page in enumerate(PAGES):
        cache = os.path.join(raw_dir, '_page%d.html' % (i + 1))
        content = base.fetch_page(page, cache, BASE + '/', offline=offline)
        for att in base.um_documents(content):
            if base.year_from_name(att['name']) != year:
                continue
            month = base.month_from_name(att['name'], year)
            for kind, flt in classify(att['name']):
                if (kind, month) in seen:      # poprawka/dupek w nazwie —
                    continue                  # tej samej pozycji nie wszczynamy
                seen.add((kind, month))
                item = {
                    'file': base.att_file(att, kind, year, month),
                    'url': att['url'],
                    'label': att['name'],
                }
                if flt:
                    item['nr_filter'] = flt
                out.append(item)
    return out, PAGES[0]
