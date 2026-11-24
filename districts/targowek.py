# -*- coding: utf-8 -*-
"""Dzielnica Targówek — rejestry WZ i ICP.

Źródło: https://targowek.um.warszawa.pl/waw/targowek/-/
warunki-zabudowy-postepowania-decyzje — 18 PDF-ów: roczne 2021–2024
plus miesięczne 2025–2026 („-czerwiec-2026.pdf”, „_11_2025.pdf”).

Rejestry:
  * wnioski — jeden plik miesięczny zawiera WZ i ICP razem
    („wszczętych postępowaniach o warunkach zabudowy i ustaleniu
    lokalizacji inwestycji celu publicznego”) — prowadzimy je jako
    wspólny rejestr „Wnioski WZ/ICP”;
  * decyzje WZ i decyzje ICP osobno.

Uwaga na rok 2022: plik „…12-2022.pdf” w nazwie brzmi jak grudzień,
a w treści ma cały rocznik (daty od stycznia) — to roczny plik
z numerem wydania w nazwie; miesięcownik od 2025.
"""
import os
import re

import parsers
from districts import base

SLUG = 'targowek'
NAME = 'Targówek'
SHORT = 'Targówek'
BASE = 'https://targowek.um.warszawa.pl'
PAGE = BASE + '/waw/targowek/-/warunki-zabudowy-postepowania-decyzje'
YEARS = list(range(2021, 2027))

_WN_COLS = [('nr', 0, 'Znak sprawy', 'nr'),
            ('inw', 0, 'Nazwa inwestycji z wniosku', 'wide'),
            ('wn', 0, 'Wnioskodawca', 'mid'),
            ('nier', 0, 'Adres inwestycji', 'mid'),
            ('dz', 0, 'Działka / obręb', '')]
_DEC_COLS = [('nr', 0, 'Nr decyzji', 'nr'),
             ('inw', 0, 'Streszczenie ustaleń', 'wide'),
             ('wn', 0, 'Wnioskodawca', 'mid'),
             ('nier', 0, 'Ulica', 'mid'),
             ('dz', 0, 'Działka / obręb', '')]

REGISTERS = [
    dict(
        id='wn_wz', match='wn_wz',
        name='Wszczęte postępowania (WZ/ICP)', short='Wnioski WZ/ICP',
        desc='Informacja o wszczętych postępowaniach w sprawie '
             'ustalenia warunków zabudowy i lokalizacji inwestycji '
             'celu publicznego.',
        header=1, date=None, by_header=True, cols=_WN_COLS,
    ),
    dict(
        id='dec_wz', match='dec_wz',
        name='Decyzje o warunkach zabudowy', short='Decyzje WZ',
        desc='Informacja o wydanych decyzjach w sprawie warunków '
             'zabudowy.',
        header=1, date=None, by_header=True, cols=_DEC_COLS,
    ),
    dict(
        id='dec_icp', match='dec_icp',
        name='Decyzje o lokalizacji inwestycji celu publicznego',
        short='Decyzje ICP',
        desc='Informacja o wydanych decyzjach w sprawie ustalenia '
             'lokalizacji inwestycji celu publicznego o znaczeniu '
             'powiatowym i gminnym.',
        header=1, date=None, by_header=True, cols=_DEC_COLS,
    ),
]


def page_url(year):
    return PAGE


def classify(text):
    t = parsers.fold(text.lower())
    if 'wszcz' in t:
        return ['wn_wz']
    if 'decyzj' in t:
        if 'lokalizacj' in t or 'celu publicznego' in t:
            return ['dec_icp']
        if 'warunk' in t or re.search(r'(^|[^a-z0-9])wz', t):
            return ['dec_wz']
    return []


def matches(cfg, fname):
    return cfg['match'] in fname.lower()


def list_sources(year, raw_dir, offline=False):
    content = base.fetch_page(PAGE, os.path.join(raw_dir, '_warunki.html'),
                              BASE + '/', offline=offline)
    out, seen = [], set()
    for att in base.um_documents(content):
        if base.year_from_name(att['name']) != year:
            continue
        month = base.month_from_name(att['name'], year)
        for kind in classify(att['name']):
            if (kind, month) in seen:
                continue
            seen.add((kind, month))
            out.append({
                'file': base.att_file(att, kind, year, month),
                'url': att['url'],
                'label': att['name'],
            })
    return out, PAGE
