# -*- coding: utf-8 -*-
"""Generator strony z rejestrami dzielnic Warszawy.

Dwa źródła danych:
  * GUNB (pliki zbiorcze) — pozwolenia na budowę dla wszystkich 18 dzielnic,
    2016–2026, aktualizacja nocna;
  * strony dzielnic — rejestry WZ/ICP tam, gdzie urząd je publikuje
    (na razie Ursus i Praga-Północ).

Wynik:
  site/index.html          — powłoka strony (mała, ładuje dane na żądanie)
  site/data/index.json     — manifest dzielnic i roczników
  site/data/<slug>/<rok>.json
"""
import argparse
import datetime as dt
import glob
import json
import os
import shutil
import sys

import gunb
import parsers
from districts import base, praga_polnoc, ursus

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'raw')
SITE = os.path.join(ROOT, 'site')
DATA = os.path.join(SITE, 'data')
TPL = os.path.join(ROOT, 'templates')

GUNB_YEARS = list(range(2016, 2027))

# Wszystkie dzielnice Warszawy. `organ` to nazwa organu w rejestrze GUNB,
# `site` to opcjonalny adapter strony dzielnicowej (WZ/ICP).
DISTRICTS = [
    dict(slug='bemowo', name='Bemowo', organ='Prezydent Miasta Warszawa - Bemowo'),
    dict(slug='bialoleka', name='Białołęka', organ='Prezydent Miasta Warszawa - Białołęka'),
    dict(slug='bielany', name='Bielany', organ='Prezydent Miasta Warszawa - Bielany'),
    dict(slug='mokotow', name='Mokotów', organ='Prezydent Miasta Warszawa - Mokotów'),
    dict(slug='ochota', name='Ochota', organ='Prezydent Miasta Warszawa - Ochota'),
    dict(slug='praga-poludnie', name='Praga-Południe', organ='Prezydent Miasta Warszawa - Praga Płd.'),
    dict(slug='praga-polnoc', name='Praga-Północ', organ=praga_polnoc.GUNB_ORGAN, site=praga_polnoc),
    dict(slug='rembertow', name='Rembertów', organ='Prezydent Miasta Warszawa - Rembertów'),
    dict(slug='srodmiescie', name='Śródmieście', organ='Prezydent Miasta Warszawa - Śródmieście'),
    dict(slug='targowek', name='Targówek', organ='Prezydent Miasta Warszawa - Targówek'),
    dict(slug='ursus', name='Ursus', organ='Prezydent Miasta Warszawa - Ursus',
         site=ursus, gunb=False),
    dict(slug='ursynow', name='Ursynów', organ='Prezydent Miasta Warszawa - Ursynów'),
    dict(slug='wawer', name='Wawer', organ='Prezydent Miasta Warszawa - Wawer'),
    dict(slug='wesola', name='Wesoła', organ='Prezydent Miasta Warszawa - Wesoła'),
    dict(slug='wilanow', name='Wilanów', organ='Prezydent Miasta Warszawa - Wilanów'),
    dict(slug='wlochy', name='Włochy', organ='Prezydent Miasta Warszawa - Włochy'),
    dict(slug='wola', name='Wola', organ='Prezydent Miasta Warszawa - Wola'),
    dict(slug='zoliborz', name='Żoliborz', organ='Prezydent Miasta Warszawa - Żoliborz'),
]


def write_json(path, obj):
    """Zapis JSON z jednym wierszem danych na linię.

    `indent=0` daje wcięcia bez spacji: plik rośnie o ~6%, ale każda pozycja
    rejestru trafia do osobnej linii. Dzięki temu diff w gicie pokazuje
    konkretne decyzje, a nie cały rocznik.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)


def build_district(dist, gunb_rows, offline=False, skip_site=False):
    """Buduje wszystkie roczniki jednej dzielnicy."""
    slug = dist['slug']
    print('\n[%s]' % dist['name'])

    by_year = {}

    # --- GUNB: pozwolenia na budowę -------------------------------------
    # Ursus ma na swojej stronie także PnB, więc GUNB pomijamy (dublowałby).
    use_gunb = dist.get('gunb', True)
    if use_gunb:
        rows = gunb_rows.get(dist['organ'], [])
        print('  GUNB: %d spraw' % len(rows))
        for year in GUNB_YEARS:
            regs = gunb.registers_for_year(rows, year)
            if regs:
                by_year.setdefault(year, []).extend(regs)

    # --- strona dzielnicy: WZ / ICP -------------------------------------
    site_mod = dist.get('site')
    if site_mod and not skip_site:
        raw_dir = os.path.join(RAW, slug)
        for year in site_mod.YEARS:
            try:
                data = base.build_year(site_mod, year, raw_dir, offline=offline)
            except Exception as e:
                print('  ! %d: %s' % (year, e))
                continue
            if data['total']:
                by_year.setdefault(year, []).extend(data['registers'])

    # --- zapis ----------------------------------------------------------
    out_dir = os.path.join(DATA, slug)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)

    sources = ((['GUNB'] if use_gunb else [])
               + ([site_mod.NAME + ' (strona dzielnicy)']
                  if site_mod and not skip_site else []))

    years = []
    for year in sorted(by_year):
        regs = by_year[year]
        total = sum(len(r['rows']) for r in regs)
        if not total:
            continue
        obj = {
            'district': slug,
            'year': year,
            'generated': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'total': total,
            'registers': regs,
        }
        write_json(os.path.join(out_dir, '%d.json' % year), obj)
        years.append({'year': year, 'total': total, 'registers': len(regs)})
        print('  %d: %4d pozycji w %d rejestrach' % (year, total, len(regs)))

    if years:
        # metadane osobno — manifest składamy ze skanu dysku, żeby CI i
        # maszyna lokalna mogły budować różne dzielnice bez nadpisywania się
        write_json(os.path.join(out_dir, 'meta.json'),
                   {'slug': slug, 'name': dist['name'], 'sources': sources})

    return {
        'slug': slug,
        'name': dist['name'],
        'years': years,
        'total': sum(y['total'] for y in years),
        'default': years[-1]['year'] if years else None,
        'sources': sources,
    }


def scan_index():
    """Manifest złożony z plików leżących na dysku.

    Dzięki temu workflow (16 dzielnic z GUNB) i maszyna lokalna (Ursus
    i Praga-Północ) budują rozłączne zbiory i wzajemnie się nie kasują.
    """
    entries = []
    if not os.path.isdir(DATA):
        return entries
    for slug in sorted(os.listdir(DATA)):
        d = os.path.join(DATA, slug)
        meta_path = os.path.join(d, 'meta.json')
        if not os.path.isdir(d) or not os.path.exists(meta_path):
            continue
        meta = json.load(open(meta_path, encoding='utf-8'))
        years = []
        for f in sorted(glob.glob(os.path.join(d, '[0-9][0-9][0-9][0-9].json'))):
            obj = json.load(open(f, encoding='utf-8'))
            years.append({'year': obj['year'], 'total': obj['total'],
                          'registers': len(obj['registers'])})
        if not years:
            continue
        entries.append({
            'slug': slug,
            'name': meta['name'],
            'years': years,
            'total': sum(y['total'] for y in years),
            'default': years[-1]['year'],
            'sources': meta.get('sources', []),
        })
    return entries


def write_index(entries):
    obj = {
        'generated': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'districts': entries,
    }
    write_json(os.path.join(DATA, 'index.json'), obj)
    return obj


def render(index):
    os.makedirs(SITE, exist_ok=True)
    tpl = open(os.path.join(TPL, 'index.html'), encoding='utf-8').read()
    css = open(os.path.join(TPL, 'style.css'), encoding='utf-8').read()
    js = open(os.path.join(TPL, 'app.js'), encoding='utf-8').read()

    logo = ''
    b64 = os.path.join(TPL, 'logo-bizu.b64')
    if os.path.exists(b64):
        logo = 'data:image/png;base64,' + open(b64, encoding='ascii').read().strip()

    total = sum(d['total'] for d in index['districts'])
    years = sorted({y['year'] for d in index['districts'] for y in d['years']})
    span = '%d–%d' % (years[0], years[-1]) if years else ''

    html = (tpl
            .replace('__STYLE__', css)
            .replace('__SCRIPT__', js)
            .replace('__LOGO__', logo)
            .replace('__COUNT__', str(total))
            .replace('__DISTRICTS__', str(len(index['districts'])))
            .replace('__YEARS__', span)
            .replace('__GENERATED__', index['generated'][:10]))
    out = os.path.join(SITE, 'index.html')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('\n  -> site/index.html  (%.0f kB)' % (os.path.getsize(out) / 1024))


def main():
    ap = argparse.ArgumentParser(description='Rejestry dzielnic Warszawy')
    ap.add_argument('--district', help='pojedyncza dzielnica (slug)')
    ap.add_argument('--gunb-only', action='store_true',
                    help='tylko dzielnice bez własnej strony (dane z GUNB)')
    ap.add_argument('--site-only', action='store_true',
                    help='tylko dzielnice z własną stroną (Ursus, Praga-Północ)')
    ap.add_argument('--skip-site', action='store_true',
                    help='pomiń strony dzielnic (tylko GUNB)')
    ap.add_argument('--offline', action='store_true', help='nie pobieraj, użyj cache')
    ap.add_argument('--render-only', action='store_true',
                    help='tylko HTML z gotowych danych')
    args = ap.parse_args()

    if args.render_only:
        render({'generated': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
                'districts': scan_index()})
        return

    targets = DISTRICTS
    if args.gunb_only:
        targets = [d for d in DISTRICTS if not d.get('site')]
    elif args.site_only:
        targets = [d for d in DISTRICTS if d.get('site')]
    if args.district:
        targets = [d for d in targets if d['slug'] == args.district]
        if not targets:
            sys.exit('nieznana dzielnica: %s' % args.district)

    # GUNB pobieramy tylko wtedy, gdy któraś z budowanych dzielnic go używa
    gunb_rows = {}
    if any(d.get('gunb', True) for d in targets):
        print('Pobieranie rejestru GUNB (Mazowsze)…')
        zip_path = gunb.download(os.path.join(RAW, 'gunb'), offline=args.offline)

        print('Czytanie pliku zbiorczego…')
        gunb_rows = gunb.read_all(zip_path, [d['organ'] for d in targets])
        for dist in targets:
            print('  %-16s %6d spraw' % (dist['name'], len(gunb_rows[dist['organ']])))

    for dist in targets:
        build_district(dist, gunb_rows,
                       offline=args.offline,
                       skip_site=args.skip_site)

    index = write_index(scan_index())
    grand = sum(d['total'] for d in index['districts'])
    print('\n  RAZEM: %d pozycji w %d dzielnicach' % (grand, len(index['districts'])))
    render(index)


if __name__ == '__main__':
    main()
