# -*- coding: utf-8 -*-
"""Dzielnica Wilanów — rejestry WZ i ICP (skumulowane).

Źródło: https://wilanow.um.warszawa.pl/waw/wilanow/
wykazy-i-informacje-o-decyzjach — cztery załączniki „Zał. 1a/1b/2/3”,
każdy opublikowany jako PDF i XLSX (bierzemy XLSX, PDF-y tego samego
rejestru są tylko zapasowe i mają mniej wierszy).

Rejestry są skumulowane (cała historia od 2020 w jednym pliku, sekcje
„2020 rok” itd.), więc roczniki wycinamy po dacie z wiersza
(by_date_year=True) — te same pliki zasilają każdy rok 2020–2026.

Wnioski WZ (Zał. 1a) i wnioski ICP (Zał. 1b) prowadzimy jako jeden
rejestr „Wnioski WZ/ICP” — zgodnie z resztą dzielnic.
"""
import os
import re

import parsers
from districts import base

SLUG = 'wilanow'
NAME = 'Wilanów'
SHORT = 'Wilanów'
BASE = 'https://wilanow.um.warszawa.pl'
PAGE = BASE + '/waw/wilanow/wykazy-i-informacje-o-decyzjach'
YEARS = list(range(2020, 2027))

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
        id='wn_wz', match=('wn_wz', 'wn_icp'),
        name='Wszczęte postępowania (WZ/ICP)', short='Wnioski WZ/ICP',
        desc='Informacja o wszczętych postępowaniach w sprawie '
             'ustalenia warunków zabudowy i lokalizacji inwestycji '
             'celu publicznego.',
        header=1, date=None, by_header=True, cols=_WN_COLS,
        by_date_year=True,
    ),
    dict(
        id='dec_wz', match='dec_wz',
        name='Decyzje o warunkach zabudowy', short='Decyzje WZ',
        desc='Informacja o wydanych decyzjach w sprawie warunków '
             'zabudowy.',
        header=1, date=None, by_header=True, cols=_DEC_COLS,
        by_date_year=True,
    ),
    dict(
        id='dec_icp', match='dec_icp',
        name='Decyzje o lokalizacji inwestycji celu publicznego',
        short='Decyzje ICP',
        desc='Informacja o wydanych decyzjach o ustaleniu lokalizacji '
             'inwestycji celu publicznego.',
        header=1, date=None, by_header=True, cols=_DEC_COLS,
        by_date_year=True,
    ),
]

# numer załącznika -> rodzaj rejestru (wn_wz = WZ+ICP razem)
_KINDS = {'1a': 'wn_wz', '1b': 'wn_icp', '2': 'dec_wz', '3': 'dec_icp'}


def page_url(year):
    return PAGE


def matches(cfg, fname):
    pats = cfg['match'] if isinstance(cfg['match'], (tuple, list)) \
        else (cfg['match'],)
    return any(p in fname.lower() for p in pats)


def _sig(name):
    """'zał. 1a' / 'zał. 2' -> '1a' / '2'; None dla innych plików."""
    low = parsers.fold(name.lower())
    if 'rejestr' not in low:
        return None
    m = re.search(r'zal\.?\s*[-–—]? *\(?([1-3])([ab]?)\b', low)
    return ('%s%s' % (m.group(1), m.group(2))) if m else None


def list_sources(year, raw_dir, offline=False):
    content = base.fetch_page(PAGE, os.path.join(raw_dir, '_wykazy.html'),
                              BASE + '/', offline=offline)
    best = {}
    for att in base.um_documents(content):
        sig = _sig(att['name'])
        if not sig or sig not in _KINDS:
            continue
        ext = os.path.splitext(att['name'])[1].lower()
        prev = best.get(sig)
        if prev is None or (ext == '.xlsx' and prev[0] != '.xlsx'):
            best[sig] = (att, ext)
    out = []
    for sig, (att, _ext) in sorted(best.items()):
        out.append({
            'file': base.att_file(att, _KINDS[sig], year),
            'url': att['url'],
            'label': att['name'],
        })
    return out, PAGE
