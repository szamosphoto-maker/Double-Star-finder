#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DuoStar Finder 1.0 – teljes WDS-katalógus geometriai felderítése WCS FITS képen.

Csak katalóguspozíciókat számol: NEM detektál, NEM mér, NEM vizsgálja a láthatóságot.
Követelmény: pip install astropy numpy
"""
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import pixel_to_skycoord, skycoord_to_pixel

DEFAULT_WDS = Path(r'D:\Astro\catalogs\wdsweb_summ2.txt')
EXTENSIONS = {'.fit', '.fits', '.fts'}

@dataclass
class Pair:
    wds: str
    disc: str
    comp: str
    pa: float
    sep: float
    mag1: float | None
    mag2: float | None
    ra: float
    dec: float


def num(txt: str):
    try:
        x = float(txt.strip())
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def parse_wds(path: Path):
    """A PhotoAnalyzer v1.3 rögzített szélességű mezőinek használata."""
    rows = []
    stats = {'lines': 0, 'missing_geometry': 0, 'bad_position': 0}
    with path.open('r', encoding='utf-8', errors='replace') as fp:
        for line in fp:
            stats['lines'] += 1
            if len(line) < 130:
                stats['bad_position'] += 1
                continue
            wds = line[0:10].strip()
            pa, sep = num(line[42:45]), num(line[52:57])
            if not wds or pa is None or sep is None or sep < 0:
                stats['missing_geometry'] += 1
                continue
            ra, dec = line[112:121].strip(), line[121:130].strip()
            try:
                if len(ra) != 9 or len(dec) != 9:
                    raise ValueError('invalid coordinate length')
                c = SkyCoord(f'{ra[:2]}h{ra[2:4]}m{ra[4:]}s',
                             f'{dec[:3]}d{dec[3:5]}m{dec[5:]}s', frame='icrs')
            except (ValueError, TypeError):
                stats['bad_position'] += 1
                continue
            rows.append(Pair(wds, line[10:17].strip(), line[17:22].strip(),
                             pa, sep, num(line[58:62]), num(line[64:69]),
                             float(c.ra.deg), float(c.dec.deg)))
    return rows, stats


def choose_file(title, filetypes):
    from tkinter import Tk, filedialog
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        value = filedialog.askopenfilename(title=title, filetypes=filetypes)
    finally:
        root.destroy()
    return Path(value) if value else None


def load_wcs(path):
    with fits.open(path, memmap=False) as hdul:
        hdu = next((h for h in hdul if h.data is not None and 'CTYPE1' in h.header), None)
        if hdu is None:
            raise ValueError('Nem található WCS-t és képadatot tartalmazó FITS-HDU.')
        header = hdu.header.copy()
        ny, nx = hdu.data.shape[-2:]
    wcs = WCS(header, naxis=2).celestial
    if not wcs.has_celestial:
        raise ValueError('A FITS nem tartalmaz használható égi WCS-t.')
    return wcs, nx, ny, header


def find_pairs(rows, wcs, nx, ny):
    center = pixel_to_skycoord((nx - 1)/2, (ny - 1)/2, wcs, origin=0)
    corners = pixel_to_skycoord([0, nx-1, 0, nx-1], [0, 0, ny-1, ny-1], wcs, origin=0)
    radius = float(np.max(center.separation(corners).deg))
    results = []
    # Előszűrés gyorsításként, de a végső feltétel kizárólag a pixelhatár.
    # A párok A komponensére előszűrünk; a sarkoknál kis biztonsági ráhagyással.
    for start in range(0, len(rows), 10000):
        batch = rows[start:start + 10000]
        coords_a = SkyCoord(ra=np.array([r.ra for r in batch])*u.deg,
                            dec=np.array([r.dec for r in batch])*u.deg, frame='icrs')
        candidate = center.separation(coords_a).deg <= radius + 0.02
        if not np.any(candidate):
            continue
        subset = [r for r, keep in zip(batch, candidate) if keep]
        a = coords_a[candidate]
        b = a.directional_offset_by(np.array([r.pa for r in subset])*u.deg,
                                     np.array([r.sep for r in subset])*u.arcsec)
        xa, ya = skycoord_to_pixel(a, wcs, origin=0, mode='all')
        xb, yb = skycoord_to_pixel(b, wcs, origin=0, mode='all')
        keep = (np.isfinite(xa) & np.isfinite(ya) & np.isfinite(xb) & np.isfinite(yb)
                & (xa >= 0) & (xa <= nx-1) & (ya >= 0) & (ya <= ny-1)
                & (xb >= 0) & (xb <= nx-1) & (yb >= 0) & (yb <= ny-1))
        for i in np.flatnonzero(keep):
            results.append((subset[i], float(a[i].ra.deg), float(a[i].dec.deg),
                            float(b[i].ra.deg), float(b[i].dec.deg)))
    results.sort(key=lambda r: (r[0].wds, r[0].disc, r[0].comp))
    return results, center


def field_number(value, decimal=2):
    return f'{value:.{decimal}f}' if value is not None else '—'


def write_report(path, fit, wds, header, rows, stats, results, center, nx, ny):
    lines = [
        'DUOSTAR FINDER 1.0 — WDS-KATALÓGUS FELDERÍTÉS',
        '=' * 116,
        f'FITS: {fit.name}',
        f'WDS: {wds}',
        f'Observation (FITS): {header.get("DATE-OBS", "nincs")}',
        f'Képméret: {nx} × {ny} pixel',
        f'Képközéppont (ICRS): RA={center.ra.deg:.8f}°, Dec={center.dec.deg:+.8f}°',
        f'Beolvasott WDS sorok: {stats["lines"]}',
        f'Használható katalóguspárok: {len(rows)}',
        f'Hiányos PA/szeparáció miatt kihagyva: {stats["missing_geometry"]}',
        f'Hiányzó/érvénytelen koordináták miatt kihagyva: {stats["bad_position"]}',
        f'Teljes egészében a képen belüli párok: {len(results)}',
        '',
        'FIGYELEM: EZ NEM CSILLAGDETEKTÁLÁS ÉS NEM MÉRÉS!',
        'A lista a WDS utolsó PA/szeparáció adataiból számított A és B pozíciókon alapul.',
        'Mindkét számított komponensnek a FITS pixelhatárain belül kell lennie.',
        'Fényességre, szeparációra és optikai felbonthatóságra nincs szűrés.',
        'A WDS koordináták és a történeti PA/szeparáció miatt a tényleges pozíció eltérhet.',
        '',
        f'{"WDS":<11} {"Discoverer":<10} {"Comp":<6} {"PA(°)":>7} {"Sep(″)":>9} {"Mag1":>6} {"Mag2":>6}  {"RA_A(deg)":>13} {"Dec_A(deg)":>13} {"RA_B(deg)":>13} {"Dec_B(deg)":>13}',
        '-' * 116,
    ]
    for row, ra_a, dec_a, ra_b, dec_b in results:
        lines.append(f'{row.wds:<11} {row.disc:<10} {row.comp or "-":<6} '
                     f'{row.pa:7.1f} {row.sep:9.2f} {field_number(row.mag1):>6} {field_number(row.mag2):>6}  '
                     f'{ra_a:13.8f} {dec_a:13.8f} {ra_b:13.8f} {dec_b:13.8f}')
    lines += ['', f'Összesen: {len(results)} WDS pár.', '']
    path.write_text('\n'.join(lines), encoding='utf-8-sig')



def write_csv(path, results):
    """TOPCAT/Excel számára szabványos UTF-8 BOM-os, vesszővel tagolt tábla."""
    columns = ['WDS', 'Discoverer', 'Components', 'PA', 'Sep',
               'Mag1', 'Mag2', 'RA_A', 'Dec_A', 'RA_B', 'Dec_B']
    with path.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.writer(fh, delimiter=',')
        writer.writerow(columns)
        for row, ra_a, dec_a, ra_b, dec_b in results:
            writer.writerow([
                row.wds, row.disc, row.comp,
                f'{row.pa:.1f}', f'{row.sep:.2f}',
                '' if row.mag1 is None else f'{row.mag1:.2f}',
                '' if row.mag2 is None else f'{row.mag2:.2f}',
                f'{ra_a:.8f}', f'{dec_a:.8f}',
                f'{ra_b:.8f}', f'{dec_b:.8f}',
            ])


def main():
    parser = argparse.ArgumentParser(description='WDS párok felderítése WCS FITS-en, mérés nélkül.')
    parser.add_argument('fits', nargs='?', help='FITS fájl (elhagyható: fájlválasztó)')
    parser.add_argument('--wds', help='Teljes WDS wdsweb_summ2.txt (elhagyható: alapútvonal/fájlválasztó)')
    args = parser.parse_args()
    fit = Path(args.fits) if args.fits else choose_file('Válaszd ki a WCS FITS képet', [('FITS', '*.fit *.fits *.fts'), ('Minden fájl', '*.*')])
    if not fit:
        print('Nincs kiválasztott FITS.')
        return 1
    wds = Path(args.wds) if args.wds else DEFAULT_WDS
    if not wds.is_file() and not args.wds:
        wds = choose_file('Válaszd ki a teljes wdsweb_summ2.txt katalógust', [('WDS TXT', '*.txt'), ('Minden fájl', '*.*')])
    if not wds or not wds.is_file():
        print('Nem található a teljes WDS katalógus.')
        return 1
    try:
        wcs, nx, ny, header = load_wcs(fit)
        rows, stats = parse_wds(wds)
        if not rows:
            raise ValueError('A katalógusból nem sikerült érvényes WDS párokat beolvasni.')
        matches, center = find_pairs(rows, wcs, nx, ny)
        out = fit.with_name(fit.stem + '_WDS_Finder.txt')
        csv_out = fit.with_name(fit.stem + '_WDS_Finder.csv')
        write_report(out, fit, wds, header, rows, stats, matches, center, nx, ny)
        write_csv(csv_out, matches)
        print(f'Kész. {len(matches)} pár található a képen.\nTXT: {out}\nCSV: {csv_out}')
        return 0
    except Exception as exc:
        print(f'HIBA: {exc}')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
