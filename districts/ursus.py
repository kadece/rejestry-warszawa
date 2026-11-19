# -*- coding: utf-8 -*-
"""Dzielnica Ursus — rejestry publikowane na ursus.um.warszawa.pl.

Źródło: strona rocznika `/wykazy-za-rok-YYYY` z załącznikami XLSX/PDF.
Roczniki 2019–2020 urząd opublikował wyłącznie w PDF.
"""
import os
import re
import urllib.parse

import parsers

SLUG = 'ursus'
NAME = 'Ursus'
SHORT = 'Ursus'
BASE = 'https://ursus.um.warszawa.pl'
YEARS = list(range(2019, 2027))

# Roczniki 2024+ mają adres z prefiksem /-/, starsze bez niego.
PAGES = (BASE + '/-/wykazy-za-rok-{year}', BASE + '/wykazy-za-rok-{year}')

# --------------------------------------------------------------------------
# Konfiguracja rejestrów
#   match     – fragment nazwy pliku (albo lista), po którym rozpoznajemy plik
#   header    – podpowiedź numeru wiersza nagłówka (parser i tak szuka „Lp.”)
#   date      – kolumna z datą (1-based)
#   cols      – (klucz, kolumna, etykieta, szerokość)
#   pdf_title – oczekiwany tytuł PDF (bez polskich znaków); chroni przed
#               podmienionym plikiem w źródle
# --------------------------------------------------------------------------

REGISTERS = [
    dict(
        id='dec_wz', match='rejestr_dec_wz',
        name='Decyzje o warunkach zabudowy', short='Decyzje WZ',
        desc='Decyzje o ustaleniu warunków zabudowy i zagospodarowania terenu.',
        header=4, date=2, pdf_title='rejestr wz',
        cols=[('nr', 2, 'Nr decyzji', 'nr'),
              ('inw', 3, 'Rodzaj inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 5, 'Nieruchomość', 'mid'),
              ('adr', 6, 'Adres', ''),
              ('roz', 7, 'Rozstrzygnięcie', '')],
    ),
    dict(
        id='dec_pnb', match='rejestr_decyzji_o_pozw_na_bud',
        name='Decyzje o pozwoleniu na budowę', short='Decyzje PnB',
        desc='Pozwolenia na budowę, rozbiórkę oraz decyzje odmowne i umorzenia.',
        header=7, date=2, pdf_title='rejestr pnb',
        cols=[('nr', 2, 'Nr decyzji', 'nr'),
              ('inw', 3, 'Rodzaj inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 5, 'Nieruchomość', 'mid'),
              ('adr', 6, 'Adres', ''),
              ('rodz', 7, 'Rodzaj decyzji', '')],
    ),
    dict(
        id='dec_lcp', match='rejestr_decyzji_lcp',
        name='Decyzje o lokalizacji inwestycji celu publicznego', short='Decyzje LCP',
        desc='Decyzje o ustaleniu lokalizacji inwestycji celu publicznego.',
        header=2, date=3, pdf_title='rejestr decyzji lcp',
        cols=[('nr', 3, 'Nr decyzji', 'nr'),
              ('organ', 2, 'Organ', 'mid'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('inw', 5, 'Rodzaj inwestycji', 'wide'),
              ('roz', 6, 'Rozstrzygnięcie', ''),
              ('teren', 7, 'Teren inwestycji', 'mid')],
    ),
    dict(
        id='dec_zrid', match='rejestr_decyzji_zrid',
        name='Decyzje ZRID', short='Decyzje ZRID',
        desc='Decyzje o zezwoleniu na realizację inwestycji drogowej.',
        header=2, date=3, pdf_title='rejestr decyzji zrid',
        cols=[('nr', 3, 'Nr decyzji', 'nr'),
              ('organ', 2, 'Organ', 'mid'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('streszcz', 5, 'Streszczenie ustaleń', 'wide'),
              ('inw', 6, 'Rodzaj inwestycji', 'wide'),
              ('teren', 7, 'Teren inwestycji', 'mid')],
    ),
    dict(
        id='wn_wz', match='rejestr_wnioskow_o_wz',
        name='Wnioski o warunki zabudowy', short='Wnioski WZ',
        desc='Wnioski o ustalenie warunków zabudowy wraz z datą wpływu.',
        header=4, date=2, pdf_title='rejestr wnioskow wz',
        cols=[('inw', 3, 'Rodzaj inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 5, 'Nieruchomość', 'mid'),
              ('adr', 6, 'Adres', '')],
    ),
    dict(
        id='wn_pnb', match='rejestr_wnioskow_o_pozw_na',
        name='Wnioski o pozwolenie na budowę', short='Wnioski PnB',
        desc='Wnioski o pozwolenie na budowę, rozbiórkę i inne opracowania.',
        header=3, date=2, pdf_title='rejestr wnioskow pnb',
        cols=[('inw', 3, 'Rodzaj inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 5, 'Nieruchomość', 'mid'),
              ('adr', 6, 'Adres', '')],
    ),
    dict(
        id='wn_lcp', match='rejestr_wnioskow_lcp',
        name='Wnioski o lokalizację inwestycji celu publicznego', short='Wnioski LCP',
        desc='Wnioski o wydanie decyzji o ustaleniu lokalizacji inwestycji celu publicznego.',
        header=2, date=2, pdf_title='rejestr wnioskow lcp',
        cols=[('inw', 3, 'Rodzaj inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 5, 'Nieruchomość', 'mid'),
              ('adr', 6, 'Adres', '')],
    ),
    dict(
        id='zgl', match='rejestr_zgloszen',
        name='Zgłoszenia robót budowlanych', short='Zgłoszenia RB',
        desc='Zgłoszenia robót budowlanych, rozbiórek i innych prac.',
        header=8, date=2, pdf_title='rejestr zgloszen',
        cols=[('inw', 3, 'Rodzaj inwestycji', 'wide'),
              ('wn', 4, 'Wnioskodawca', 'mid'),
              ('nier', 5, 'Nieruchomość', 'mid'),
              ('adr', 6, 'Adres', '')],
    ),
    dict(
        id='umowy16', match=['rejestr_umowyart16', 'art.+16', 'art. 16'],
        name='Umowy z art. 16 ustawy o drogach publicznych', short='Umowy art. 16',
        desc='Umowy z inwestorami o budowę dróg, podpisane na podstawie '
             'art. 16 ustawy o drogach publicznych.',
        header=3, date=4, pdf_title=None,
        cols=[('nr', 2, 'Nr umowy', 'nr'),
              ('inwestor', 3, 'Inwestor', 'mid'),
              ('przedmiot', 5, 'Przedmiot umowy', 'wide')],
    ),
]


def page_url(year):
    return PAGES[0].format(year=year)


def matches(cfg, fname):
    pats = cfg['match']
    if isinstance(pats, str):
        pats = [pats]
    return any(p in fname for p in pats)


def list_sources(year, raw_dir, offline=False):
    """Załączniki ze strony rocznika. HTML cache'owany w raw/<rok>.html."""
    cache = os.path.join(raw_dir, '%d.html' % year)
    if offline:
        if not os.path.exists(cache):
            raise RuntimeError('brak pliku %s' % os.path.basename(cache))
        with open(cache, encoding='utf-8', errors='replace') as f:
            return _parse_attachments(f.read()), page_url(year)

    last = None
    for tpl in PAGES:
        url = tpl.format(year=year)
        try:
            html = parsers.fetch(url, BASE + '/').decode('utf-8', 'replace')
        except Exception as e:
            last = e
            continue
        os.makedirs(raw_dir, exist_ok=True)
        with open(cache, 'w', encoding='utf-8') as f:
            f.write(html)
        return _parse_attachments(html), url
    raise last


def _parse_attachments(html):
    out = []
    for m in re.finditer(
            r'<a\s+href="([^"]+)"[^>]*class="attachment-link"[^>]*>(.*?)</a>',
            html, re.S):
        url, inner = m.group(1), m.group(2)
        nm = re.search(r'class="attachment-name"[^>]*>(.*?)</span>', inner, re.S)
        label = re.sub(r'<[^>]+>', '', nm.group(1)).strip() if nm else ''
        fname = url.split('/')[-2] if url.count('/') > 3 else url.split('/')[-1]
        fname = urllib.parse.unquote(fname.split('?')[0])
        out.append({'file': fname, 'url': url, 'label': label})
    return out
