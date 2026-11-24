# -*- coding: utf-8 -*-
"""Dzielnica Bemowo — jawność procesu inwestycyjnego.

Źródło: https://bemowo.um.warszawa.pl/jawnosc-procesu-inwestycyjnego
Jedna strona z informacjami rocznymi (od 2018, rejestry WZ, ICP
i wszczęte postępowania). Roczniki 2024+ to arkusze „Informacja o…”,
starsze bywają PDF-ami lub arkuszami „stan na 31 grudnia” — rok
i typ rejestru czytamy z nazwy pliku.

Układ arkuszy jest zgodny z resztą m.st. Warszawy (nagłówki
mapowane po treści: by_header), więc zmiana kolejności kolumn
między rocznikami nie psuje parsowania.
"""
import os
import re

import parsers
from districts import base

SLUG = 'bemowo'
NAME = 'Bemowo'
SHORT = 'Bemowo'
BASE = 'https://bemowo.um.warszawa.pl'
PAGE = BASE + '/jawnosc-procesu-inwestycyjnego'
YEARS = list(range(2018, 2027))

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
        id='dec_icp', match='dec_icp',
        name='Decyzje o lokalizacji inwestycji celu publicznego',
        short='Decyzje ICP',
        desc='Informacja o wydanych decyzjach w sprawie o ustalenie '
             'lokalizacji inwestycji celu publicznego o znaczeniu '
             'powiatowym i gminnym.',
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
        desc='Informacja o wszczętych postępowaniach o warunkach zabudowy '
             'i ustaleniu lokalizacji inwestycji celu publicznego.',
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
    # kolejność ważna: „wszczętych postępowaniach o warunkach zabudowy…”
    # zawiera na końcu to samo co rejestr WZ, więc wn testujemy pierwsze
    if 'wszcz' in t:
        return 'wn_wz'
    if 'licp' in t or 'lokalizac' in t:
        return 'dec_icp'
    if 'warunk' in t and 'zabudow' in t:
        return 'dec_wz'
    if re.search(r'decyzje[-_ ]?wz', t):            # „wydane-decyzje-WZ_2018.pdf”
        return 'dec_wz'
    return None


def matches(cfg, fname):
    return cfg['match'] in fname.lower()


def list_sources(year, raw_dir, offline=False):
    """Załączniki dla jednego rocznika.

    Roczniki 2018–2020 różnią się nazewnictwem („wydane-decyzje-WZ”,
    „rejestr decyzji o warunkach…”, pliki miesięczne wszczęć za 2020) —
    klasyfikujemy po treści nazwy, a deduplikujemy po samej nazwie:
    dwa wpisy o tej samej nazwie to poprawka tego samego arkusza
    (strona listuje od najnowszego, więc bierzemy pierwsze).
    """
    content = base.fetch_page(PAGE, os.path.join(raw_dir, '_jawnosc.html'),
                              BASE + '/', offline=offline)
    out, seen = [], set()
    for att in base.um_documents(content):
        kind = classify(att['name'])
        if kind is None:
            continue
        m = re.search(r'(20\d{2})', att['name'])
        if not m or int(m.group(1)) != year:
            continue
        if att['name'] in seen:                  # poprawka pliku — pierwsza wygrywa
            continue
        seen.add(att['name'])
        out.append({
            'file': base.att_file(att, kind, year),
            'url': att['url'],
            'label': att['name'],
        })
    return out, PAGE
