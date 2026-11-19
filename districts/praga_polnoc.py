# -*- coding: utf-8 -*-
"""Dzielnica Praga-Północ — rejestry WZ i ICP ze strony dzielnicy.

Źródło: https://pragapn.um.warszawa.pl/-/ogloszenia-2 — jedna strona z ~155
załącznikami miesięcznymi. Nazwy plików są niespójne („czerwiec.xlsx”,
„decyzje wz czerwiec 2026.xlsx”, „icp IV.xlsx”), więc typ i miesiąc czytamy
z **tekstu linku**, a nie z nazwy pliku:

    „Informacja o wydanych decyzjach o warunkach zabudowy - Październik 2026 r.”
    „Informacja o wydanych decyzjach w sprawie ustalenia lokalizacji inwestycji
      celu publicznego o znaczeniu powiatowym i gminnym - Listopad 2025 r.”
    „informacja o wszczętych postępowaniach w sprawie ustalenia warunków
      zabudowy i ustalenia inwestycji celu publicznego - Październik 2026 r.”

Pliki są miesięczne (nie kumulatywne), więc rocznik to suma dwunastu plików.
Dla tego samego (typ, rok, miesiąc) bywa kilka wersji — bierzemy pierwszą,
bo strona listuje od najnowszego.
"""
import os
import re
import urllib.parse

import parsers

SLUG = 'praga-polnoc'
NAME = 'Praga-Północ'
SHORT = 'Praga-Płn'
BASE = 'https://pragapn.um.warszawa.pl'
PAGE = BASE + '/-/ogloszenia-2'
YEARS = list(range(2021, 2027))

# Organ w rejestrze GUNB — łączy ten moduł z danymi o pozwoleniach.
GUNB_ORGAN = 'Prezydent Miasta Warszawa - Praga Pn.'

MONTHS = {
    'styczen': 1, 'stycznia': 1, 'luty': 2, 'lutego': 2, 'marzec': 3,
    'marca': 3, 'kwiecien': 4, 'kwietnia': 4, 'maj': 5, 'maja': 5,
    'czerwiec': 6, 'czerwca': 6, 'lipiec': 7, 'lipca': 7, 'sierpien': 8,
    'sierpnia': 8, 'wrzesien': 9, 'wrzesnia': 9, 'pazdziernik': 10,
    'pazdziernika': 10, 'listopad': 11, 'listopada': 11, 'grudzien': 12,
    'grudnia': 12,
}

REGISTERS = [
    dict(
        id='dec_wz', match='dec_wz',
        name='Decyzje o warunkach zabudowy', short='Decyzje WZ',
        desc='Decyzje o ustaleniu warunków zabudowy wydane przez Zarząd Dzielnicy.',
        header=4, date=3, by_header=True,
        cols=[('nr', 2, 'Nr decyzji', 'nr'),
              ('inw', 5, 'Streszczenie ustaleń', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 6, 'Nieruchomość', 'mid'),
              ('dz', 7, 'Działka / obręb', '')],
    ),
    dict(
        id='dec_icp', match='dec_icp',
        name='Decyzje o lokalizacji inwestycji celu publicznego', short='Decyzje ICP',
        desc='Decyzje o ustaleniu lokalizacji inwestycji celu publicznego '
             'o znaczeniu powiatowym i gminnym.',
        header=4, date=3, by_header=True,
        cols=[('nr', 2, 'Nr decyzji', 'nr'),
              ('inw', 5, 'Streszczenie ustaleń', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 6, 'Nieruchomość', 'mid'),
              ('dz', 7, 'Działka / obręb', '')],
    ),
    dict(
        id='wn_wz', match='wn_wz',
        name='Wszczęte postępowania (wnioski)', short='Wnioski',
        desc='Informacja o wszczętych postępowaniach w sprawie ustalenia '
             'warunków zabudowy i lokalizacji inwestycji celu publicznego.',
        header=4, date=3, by_header=True,
        cols=[('nr', 2, 'Znak sprawy', 'nr'),
              ('inw', 5, 'Nazwa inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 6, 'Adres inwestycji', 'mid'),
              ('dz', 7, 'Działka / obręb', '')],
    ),
]


def page_url(year=None):
    return PAGE


def matches(cfg, fname):
    return cfg['match'] in fname


def classify(text):
    t = parsers.fold(text.lower())
    if 'wydanych decyzjach o warunkach zabudowy' in t:
        return 'dec_wz'
    if 'wydanych decyzjach w sprawie ustalenia lokalizacji' in t:
        return 'dec_icp'
    if 'wszczetych postepowaniach' in t:
        return 'wn_wz'
    return None


def month_year(text):
    t = parsers.fold(text.lower())
    for m in re.finditer(r'([a-z]+)\s+(\d{4})', t):
        if m.group(1) in MONTHS:
            return MONTHS[m.group(1)], int(m.group(2))
    return None, None


def list_sources(year, raw_dir, offline=False):
    """Załączniki dla jednego rocznika, wybrane z całej listy ogłoszeń."""
    cache = os.path.join(raw_dir, '_ogloszenia.html')
    if offline:
        if not os.path.exists(cache):
            raise RuntimeError('brak pliku %s' % os.path.basename(cache))
        with open(cache, encoding='utf-8', errors='replace') as f:
            html = f.read()
    else:
        html = parsers.fetch(PAGE, BASE + '/').decode('utf-8', 'replace')
        os.makedirs(raw_dir, exist_ok=True)
        with open(cache, 'w', encoding='utf-8') as f:
            f.write(html)

    seen = set()
    out = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        href, inner = m.group(1), m.group(2)
        if 'documents/' not in href:
            continue
        label = re.sub(r'<[^>]+>', ' ', inner)
        label = re.sub(r'\s+', ' ', label).strip()
        kind = classify(label)
        mo, yr = month_year(label)
        if not kind or yr != year:
            continue
        key = (kind, mo)
        if key in seen:                       # strona listuje od najnowszego
            continue
        seen.add(key)

        fname = urllib.parse.unquote(href.split('/')[-2])
        stem, ext = os.path.splitext(fname)
        ext = ext.lower() or '.xlsx'
        out.append({
            'file': '%s_%04d_%02d_%s%s' % (kind, yr, mo or 0,
                                           parsers.safe_name(stem, 50), ext),
            'url': href,
            'label': label,
        })
    return out, PAGE
