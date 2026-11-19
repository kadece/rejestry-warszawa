# -*- coding: utf-8 -*-
"""Wspólna logika budowy rocznika — identyczna dla każdej dzielnicy.

Dzielnica dostarcza tylko:
  * metadane (slug, nazwa, adresy),
  * konfigurację rejestrów (jak rozpoznać plik, jak nazwać kolumny),
  * `list_sources(year)` — listę załączników dla rocznika.

Reszta (pobieranie, parsowanie, składanie JSON-a) jest tutaj.
"""
import datetime as dt
import os

import parsers


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
            if part:
                rows.extend(part)
                used.append(att['file'])

        if not rows:
            print('  - pominięto %s (brak pozycji)' % cfg['id'])
            continue

        rows.sort(key=lambda x: (x['d'] is None, x['d'] or '9999-99-99'))
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
