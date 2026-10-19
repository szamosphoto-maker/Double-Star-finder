"""DuoStar Finder GUI – WDS-geometriai felderítés WCS FITS képeken.
A számításokat a változatlan duostar_finder.py modul végzi.
"""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import duostar_finder as engine


class FinderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('DuoStar Finder – WDS felderítés')
        self.geometry('920x680')
        self.minsize(750, 520)
        self.wds_path = tk.StringVar(value=str(engine.DEFAULT_WDS) if engine.DEFAULT_WDS.is_file() else '')
        self.status = tk.StringVar(value='Készen áll.')
        self.files: list[Path] = []
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.build_ui()
        self.after(100, self.poll_events)

    def build_ui(self):
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='DuoStar Finder', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='WDS-katalóguspozíciók keresése WCS FITS képeken – nem csillagdetektálás és nem mérés.').pack(anchor='w', pady=(1, 12))
        top = ttk.LabelFrame(outer, text='WDS-katalógus', padding=8)
        top.pack(fill='x', pady=(0, 9))
        ttk.Entry(top, textvariable=self.wds_path).pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.wds_button = ttk.Button(top, text='Tallózás...', command=self.choose_wds)
        self.wds_button.pack(side='right')
        selection = ttk.LabelFrame(outer, text='FITS-képek (.fit, .fits, .fts)', padding=8)
        selection.pack(fill='both', expand=False)
        row = ttk.Frame(selection)
        row.pack(fill='x', pady=(0, 6))
        self.add_button = ttk.Button(row, text='Képek hozzáadása...', command=self.choose_fits)
        self.add_button.pack(side='left')
        self.clear_button = ttk.Button(row, text='Lista törlése', command=self.clear_fits)
        self.clear_button.pack(side='left', padx=8)
        self.open_folder_button = ttk.Button(row, text='Célkönyvtár megnyitása', command=self.open_output_folder)
        self.open_folder_button.pack(side='left', padx=(0, 8))
        self.count_label = ttk.Label(row, text='0 kiválasztott kép')
        self.count_label.pack(side='right')
        listframe = ttk.Frame(selection)
        listframe.pack(fill='both', expand=False)
        self.file_list = tk.Listbox(listframe, height=6, selectmode='extended')
        self.file_list.pack(side='left', fill='both', expand=True)
        ys = ttk.Scrollbar(listframe, orient='vertical', command=self.file_list.yview)
        ys.pack(side='right', fill='y')
        self.file_list.configure(yscrollcommand=ys.set)
        options = ttk.Frame(outer)
        options.pack(fill='x', pady=10)
        self.save_csv = tk.BooleanVar(value=True)
        self.save_txt = tk.BooleanVar(value=True)
        self.csv_check = ttk.Checkbutton(options, text='CSV (TOPCAT)', variable=self.save_csv)
        self.csv_check.pack(side='left')
        self.txt_check = ttk.Checkbutton(options, text='TXT jelentés', variable=self.save_txt)
        self.txt_check.pack(side='left', padx=(14, 0))
        self.start_button = ttk.Button(options, text='Felderítés indítása', command=self.start)
        self.start_button.pack(side='right')
        logbox = ttk.LabelFrame(outer, text='Feldolgozási napló', padding=8)
        logbox.pack(fill='both', expand=True)
        self.log = tk.Text(logbox, wrap='none', height=12, state='disabled', font=('Consolas', 9))
        self.log.grid(row=0, column=0, sticky='nsew')
        scroll_y = ttk.Scrollbar(logbox, orient='vertical', command=self.log.yview)
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x = ttk.Scrollbar(logbox, orient='horizontal', command=self.log.xview)
        scroll_x.grid(row=1, column=0, sticky='ew')
        self.log.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        logbox.rowconfigure(0, weight=1)
        logbox.columnconfigure(0, weight=1)
        ttk.Label(outer, textvariable=self.status).pack(fill='x', pady=(8, 0))

    def choose_wds(self):
        chosen = filedialog.askopenfilename(title='Teljes WDS-katalógus', filetypes=[('TXT katalógus', '*.txt'), ('Minden fájl', '*.*')])
        if chosen:
            self.wds_path.set(chosen)

    def choose_fits(self):
        chosen = filedialog.askopenfilenames(title='WCS FITS képek', filetypes=[('FITS képek', '*.fit *.fits *.fts'), ('Minden fájl', '*.*')])
        existing = set(self.files)
        for item in chosen:
            path = Path(item)
            if path not in existing:
                self.files.append(path)
                existing.add(path)
                self.file_list.insert('end', str(path))
        self.count_label.configure(text=f'{len(self.files)} kiválasztott kép')

    def open_output_folder(self):
        """A kijelölt FITS mellé mentett eredmények mappáját nyitja meg."""
        if not self.files:
            messagebox.showinfo('Célkönyvtár', 'Előbb válassz ki legalább egy FITS-képet.')
            return
        selected = self.file_list.curselection()
        index = selected[0] if selected else 0
        folder = self.files[index].parent
        try:
            os.startfile(str(folder))  # Windows Intéző; a kész EXE Windowsra készül.
        except Exception as exc:
            messagebox.showerror('Célkönyvtár', f'Nem sikerült megnyitni a könyvtárat:\n{folder}\n\n{exc}')

    def clear_fits(self):
        self.files.clear()
        self.file_list.delete(0, 'end')
        self.count_label.configure(text='0 kiválasztott kép')

    def append_log(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', str(msg).rstrip() + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def emit(self, kind, value):
        self.events.put((kind, value))

    def set_busy(self, flag):
        self.busy = flag
        state = 'disabled' if flag else 'normal'
        for control in (self.start_button, self.wds_button, self.add_button, self.clear_button, self.csv_check, self.txt_check):
            control.configure(state=state)

    def start(self):
        if self.busy:
            return
        wds = Path(self.wds_path.get().strip())
        if not wds.is_file():
            messagebox.showerror('Hiányzó katalógus', 'Válassz ki egy létező teljes WDS-katalógusfájlt.')
            return
        if not self.files:
            messagebox.showerror('Hiányzó képek', 'Válassz legalább egy FITS-képet.')
            return
        if not (self.save_csv.get() or self.save_txt.get()):
            messagebox.showerror('Hiányzó kimenet', 'Legalább egy kimeneti formátumot jelölj be.')
            return
        self.set_busy(True)
        self.status.set('Katalógus beolvasása...')
        self.append_log(f'Indítás: {len(self.files)} FITS; WDS: {wds}')
        threading.Thread(target=self.work, args=(wds, list(self.files), self.save_csv.get(), self.save_txt.get()), daemon=True).start()

    def work(self, wds, files, save_csv, save_txt):
        try:
            rows, stats = engine.parse_wds(wds)
            if not rows:
                raise ValueError('A katalógus nem tartalmaz feldolgozható WDS-párokat.')
            self.emit('log', f'WDS beolvasva: {stats["lines"]} sor; használható: {len(rows)}; hiányos PA/szeparáció: {stats["missing_geometry"]}; hibás koordináta: {stats["bad_position"]}')
        except Exception as exc:
            self.emit('log', f'HIBA a WDS beolvasásakor: {exc}')
            self.emit('done', (0, len(files), 0))
            return
        ok, failed, found = 0, 0, 0
        for i, fit in enumerate(files, 1):
            self.emit('status', f'Feldolgozás {i}/{len(files)}: {fit.name}')
            self.emit('log', f'\n{"=" * 78}\n[{i}/{len(files)}] FITS: {fit}')
            try:
                wcs, nx, ny, header = engine.load_wcs(fit)
                matches, center = engine.find_pairs(rows, wcs, nx, ny)
                self.emit('log', f'Megfigyelés (FITS): {header.get("DATE-OBS", "nincs")} | {nx} × {ny} px | RA={center.ra.deg:.8f}°, Dec={center.dec.deg:+.8f}°')
                self.emit('log', f'Teljes egészében képen belüli párok: {len(matches)}')
                for pair, *_ in matches:
                    self.emit('log', f'  {pair.wds:10} {pair.disc:10} {pair.comp or "-":5}  PA={pair.pa:6.1f}°  Sep={pair.sep:8.2f}″  Mag1={engine.field_number(pair.mag1)}  Mag2={engine.field_number(pair.mag2)}')
                if save_txt:
                    txt = fit.with_name(fit.stem + '_WDS_Finder.txt')
                    engine.write_report(txt, fit, wds, header, rows, stats, matches, center, nx, ny)
                    self.emit('log', f'TXT mentve: {txt}')
                if save_csv:
                    csv = fit.with_name(fit.stem + '_WDS_Finder.csv')
                    engine.write_csv(csv, matches)
                    self.emit('log', f'CSV mentve: {csv}')
                ok += 1
                found += len(matches)
            except Exception as exc:
                failed += 1
                self.emit('log', f'HIBA: {type(exc).__name__}: {exc}')
        self.emit('done', (ok, failed, found))

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'log':
                    self.append_log(value)
                elif kind == 'status':
                    self.status.set(value)
                elif kind == 'done':
                    ok, failed, found = value
                    msg = f'Kész: {ok} feldolgozott kép, {failed} hiba, {found} katalóguspár (képenként számolva).'
                    self.append_log('\n' + msg)
                    self.status.set(msg)
                    self.set_busy(False)
        except queue.Empty:
            pass
        self.after(100, self.poll_events)


if __name__ == '__main__':
    FinderGUI().mainloop()
