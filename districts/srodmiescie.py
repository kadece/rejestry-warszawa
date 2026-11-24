# -*- coding: utf-8 -*-
"""Dzielnica Śródmieście — rejestry WZ.

Źródło: https://srodmiescie.um.warszawa.pl/-/decyzje-warunki-zabudowy
Jedna strona z informacjami miesięcznymi „NN_DECYZJE_WZ_YYYY.xlsx”
(od kwietnia 2020; 2020 ma tylko ostatnie miesiące). Nazwa pliku
powstaje z prefixu numeru miesiąca.

Układ arkuszy jest zgodny z resztą m.st. Warszawy (nagłówki
mapowane po treści: by_header), więc zmiana kolejności kolumn
między rocznikami nie psuje parsowania.
"""
import os
import re

import parsers
from districts import base

SLUG = 'srodmiescie'
NAME = 'Śródmieście'
SHORT = 'Śródmieście'
BASE = 'https://srodmiescie.um.warszawa.pl'
PAGE = BASE + '/-/decyzje-warunki-zabudowy'
YEARS = list(range(2020, 2027))

KINDS = [
    ('dec_wz', 'decyzje_wz'),
]

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
]


def page_url(year):
    return PAGE


def classify(text):
    t = parsers.fold(text.lower())
    for kind, pat in KINDS:
        if pat in t:
            return kind
    return None


def matches(cfg, fname):
    return cfg['match'] in fname.lower()


def list_sources(year, raw_dir, offline=False):
    """Załączniki dla jednego rocznika (pliki miesięczne)."""
    content = base.fetch_page(PAGE, os.path.join(raw_dir, '_decyzje_wz.html'),
                              BASE + '/', offline=offline)
    out, seen = [], set()
    for att in base.um_documents(content):
        kind = classify(att['name'])
        if kind is None:
            continue
        m = re.search(r'(20\d{2})', att['name'])
        if not m or int(m.group(1)) != year:
            continue
        mo = re.match(r'\s*0*(\d{1,2})_', att['name'])
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
