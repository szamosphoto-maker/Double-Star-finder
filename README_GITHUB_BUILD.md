# DuoStar Finder – saját használatú Windows GUI

A csomag két Python fájlt tartalmaz:
- `duostar_finder.py`: az eredeti v1.0 felderítési algoritmus, változtatás nélkül;
- `duostar_finder_gui.py`: kezelőfelület, több FITS kiválasztása, teljes görgethető napló és „Célkönyvtár megnyitása” gomb.

A WDS teljes katalógusfájlját a GUI-ban kell kiválasztani (nem része az EXE-nek).
A TXT és CSV eredmények a FITS-képek mellé kerülnek a megszokott fájlnévvel. A „Célkönyvtár megnyitása” gomb a listában kijelölt kép mappáját nyitja meg; kijelölés nélkül az első kép mappáját.

## GitHub EXE

1. Hozz létre egy privát repositoryt.
2. A csomag tartalmát a megadott mappaszerkezettel töltsd fel. A workflow útvonala: `.github/workflows/build-windows.yml`.
3. Actions → Build DuoStar Finder Windows EXE → Run workflow.
4. A futás Summary → Artifacts részében: `DuoStar_Finder_Windows`.

## Helyi próba

`pip install astropy numpy` majd `python duostar_finder_gui.py`.

Fontos: a felderítés katalogizált A/B pozíciókat vetít a FITS-re; nem ellenőrzi a csillagok valódi detektálhatóságát. A GUI párszáma a képenkénti találatok összege, ismétlődő párok is számítanak.
