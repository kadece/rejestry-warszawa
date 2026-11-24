# -*- coding: utf-8 -*-
"""Dzielnica Wawer — dokumenty budowlane.

Źródło: https://wawer.um.warszawa.pl/dokumenty-budowlane
Strona listuje pliki miesięczne „decyzje_WZ_MM_YYYY.xlsx” dla roku
bieżącego — starsze roczniki raz leżą (arkusze roczne), raz znikają
z listy. Adapter bierze wszystko, co rozpozna; starsze arkusze
roczne (2020 i wcześniejsze, „Nr decyzji i data” w jednej komórce,
bez kolumny Lp.) mają układ, którego wspólny parser nie obsługuje —
te lata po prostu zostają z samego GUNB (PnB 2016+).

Ponadto strona publikuje decyzje PnB — te pomijamy (dublowałyby
rejestr GUNB). Wszczęcia postępowań (WZ+CP w jednym arkuszu)
łapiemy jako jeden rejestr „Wnioski WZ/ICP".

Układ arkuszy jest zgodny z resztą m.st. Warszawy (nagłówki
mapowane po treści: by_header), więc zmiana kolejności kolumn
między plikami nie psuje parsowania.
"""
import os
import re

import parsers
from districts import base

SLUG = 'wawer'
NAME = 'Wawer'
SHORT = 'Wawer'
BASE = 'https://wawer.um.warszawa.pl'
PAGE = BASE + '/dokumenty-budowlane'
YEARS = list(range(2020, 2027))

REGISTERS = [
    dict(
        id='dec_wz', match='dec_wz',
        name='Decyzje o warunkach zabudowy', short='Decyzje WZ',
        desc='Informacja o wydanych decyzjach w sprawie warunków zabudowy.',
        header=1, date=None, by_header=True,
        cols=[('nr', 0, 'Nr decyzji', 'nr'),
              ('inw', 0, 'Streszczenie ustaleń', 'wide'),
              ('wn', 0, 'Wnioskodawca', 'mid'),
              ('nier', 0, 'Nieruchomość (ulica)', 'mid'),
              ('dz', 0, 'Działka / obręb', '')],
    ),
    dict(
        id='dec_cp', match='dec_cp',
        name='Decyzje o lokalizacji inwestycji celu publicznego',
        short='Decyzje CP',
        desc='Informacja o wydanych decyzjach o ustaleniu lokalizacji '
             'inwestycji celu publicznego.',
        header=1, date=None, by_header=True,
        cols=[('nr', 0, 'Nr decyzji', 'nr'),
              ('inw', 0, 'Streszczenie ustaleń', 'wide'),
              ('wn', 0, 'Wnioskodawca', 'mid'),
              ('nier', 0, 'Nieruchomość (ulica)', 'mid'),
              ('dz', 0, 'Działka / obręb', '')],
    ),
    dict(
        id='wn_wz', match='wn_wz',
        name='Wszczęte postępowania (WZ/ICP)', short='Wnioski WZ/ICP',
        desc='Informacja o wszczętych postępowaniach w sprawie '
             'ustalenia warunków zabudowy i lokalizacji inwestycji '
             'celu publicznego.',
        header=1, date=None, by_header=True,
        cols=[('nr', 0, 'Znak sprawy', 'nr'),
              ('inw', 0, 'Nazwa inwestycji', 'wide'),
              ('wn', 0, 'Wnioskodawca', 'mid'),
              ('nier', 0, 'Adres inwestycji', 'mid'),
              ('dz', 0, 'Działka / obręb', '')],
    ),
]


def page_url(year):
    return PAGE


def classify(text):
    t = parsers.fold(text.lower())
    # decyzje PnB pomijamy: siedzą w rejestrze GUNB (dublowałyby)
    if 'wniosk' in t or 'pb' in t:
        return None
    if 'wszcz' in t:
        return 'wn_wz'
    if re.search(r'decyzje[-_ ]?wz', t) or ('warunk' in t and 'zabudow' in t):
        return 'dec_wz'
    if re.search(r'decyzje[-_ ]?cp', t) or 'cel publiczny' in t:
        return 'dec_cp'
    return None


def matches(cfg, fname):
    return cfg['match'] in fname.lower()


def list_sources(year, raw_dir, offline=False):
    """Załączniki dla jednego rocznika (pliki miesięczne)."""
    content = base.fetch_page(PAGE, os.path.join(raw_dir, '_dokumenty_budowlane.html'),
                              BASE + '/', offline=offline)
    out, seen = [], set()
    for att in base.um_documents(content):
        kind = classify(att['name'])
        if kind is None:
            continue
        m = re.search(r'(20\d{2})', att['name'])
        if not m or int(m.group(1)) != year:
            continue
        mo = re.search(r'[_ ]0*(\d{1,2})_%d(?!\d)' % year, att['name'])
        month = int(mo.group(1)) if mo else 0
        if (kind, month) in seen:             # strona listuje od najnowszego
            continue
        seen.add((kind, month))
        out.append({
            'file': base.att_file(att, kind, year, month),
            'url': att['url'],
            'label': att['name'],
        })
    return out, PAGE
