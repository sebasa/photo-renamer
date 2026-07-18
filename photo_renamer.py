# photo_renamer.py
# Requiere: pip install Pillow
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ExifTags

EXIF_DATETIME_TAGS = ("DateTimeOriginal", "DateTimeDigitized", "DateTime")
IMG_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".webp", ".cr2", ".nef", ".arw", ".dng"}
OUT_FMT = "%Y-%m-%d %H-%M-%S"


def get_exif_datetime(path: Path):
    try:
        with Image.open(path) as img:
            exif = img._getexif()
            if not exif:
                return None
            tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
            for tag in EXIF_DATETIME_TAGS:
                if tag in tag_map and tag_map[tag]:
                    raw = str(tag_map[tag]).strip()
                    # Formato EXIF tipico: "YYYY:MM:DD HH:MM:SS"
                    try:
                        return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        try:
                            return datetime.strptime(raw[:19], "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            continue
    except Exception:
        return None
    return None


def get_mtime_datetime(path: Path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return None


def resolve_datetime(path: Path, source: str):
    """source en {'exif', 'mtime', 'exif_then_mtime'}"""
    if source == "exif":
        return get_exif_datetime(path), "EXIF"
    if source == "mtime":
        return get_mtime_datetime(path), "MTIME"
    # exif_then_mtime
    dt = get_exif_datetime(path)
    if dt:
        return dt, "EXIF"
    return get_mtime_datetime(path), "MTIME (fallback)"


def build_new_name(dt: datetime, original: Path, used_names: set):
    base = dt.strftime(OUT_FMT)
    ext = original.suffix.lower()
    candidate = f"{base}{ext}"
    i = 1
    while candidate.lower() in used_names or ((original.parent / candidate).exists() and (original.parent / candidate) != original):
        candidate = f"{base}_{i}{ext}"
        i += 1
    used_names.add(candidate.lower())
    return candidate


class ManualDateDialog(tk.Toplevel):
    def __init__(self, parent, initial=None):
        super().__init__(parent)
        self.title("Fecha y hora manual")
        self.resizable(False, False)
        self.result = None  # tupla (datetime, keep_time: bool)
        self.transient(parent)
        self.grab_set()

        if initial is None:
            initial = datetime.now().replace(microsecond=0)

        frm = ttk.Frame(self, padding=10)
        frm.pack()

        ttk.Label(
            frm,
            text=("Formato: YYYY-MM-DD HH:MM:SS\n"
                  "Si dejas la hora en blanco (solo YYYY-MM-DD),\n"
                  "se conserva la hora original de cada archivo.")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.var = tk.StringVar(value=initial.strftime("%Y-%m-%d %H:%M:%S"))
        entry = ttk.Entry(frm, textvariable=self.var, width=24)
        entry.grid(row=1, column=0, columnspan=2, pady=4)
        entry.focus_set()
        entry.select_range(0, "end")

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btns, text="Aceptar", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=4)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        raw = self.var.get().strip()
        # Primero intentamos fecha completa
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
            self.result = (dt, False)
            self.destroy()
            return
        except ValueError:
            pass
        # Despues intentamos solo fecha
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
            self.result = (dt, True)  # keep_time = True
            self.destroy()
            return
        except ValueError:
            pass

        messagebox.showerror(
            "Formato invalido",
            "Usa: YYYY-MM-DD HH:MM:SS  (o solo YYYY-MM-DD para mantener la hora original)",
            parent=self
        )


class PickSourceFileDialog(tk.Toplevel):
    def __init__(self, parent, candidates):
        """candidates: lista de tuplas (display_text, datetime, path)"""
        super().__init__(parent)
        self.title("Copiar fecha de otro archivo")
        self.geometry("700x400")
        self.result = None
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="Elegi el archivo del cual copiar la fecha:", padding=8).pack(anchor="w")

        cols = ("file", "datetime")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("file", text="Archivo")
        self.tree.heading("datetime", text="Fecha actual planificada")
        self.tree.column("file", width=480, anchor="w")
        self.tree.column("datetime", width=180, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8)

        self._map = {}
        for display, dt, path in candidates:
            iid = self.tree.insert("", "end", values=(display, dt.strftime(OUT_FMT) if dt else "-"))
            self._map[iid] = (dt, path)

        btns = ttk.Frame(self, padding=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Aceptar", command=self._ok).pack(side="right", padx=4)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="right", padx=4)

        self.tree.bind("<Double-1>", lambda e: self._ok())

    def _ok(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Elegi un archivo.", parent=self)
            return
        dt, path = self._map[sel[0]]
        if dt is None:
            messagebox.showwarning("Sin fecha", "Ese archivo no tiene fecha resuelta.", parent=self)
            return
        self.result = (dt, path)
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Renombrador de Fotos - YYYY-MM-DD HH-MM-SS")
        self.geometry("1100x650")
        self.folder = tk.StringVar()
        self.recursive = tk.BooleanVar(value=False)
        self.source_var = tk.StringVar(value="exif_then_mtime")
        self.rows = []  # lista de dicts con info por archivo
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Button(top, text="Elegir carpeta...", command=self.choose_folder).pack(side="left")
        ttk.Entry(top, textvariable=self.folder, width=70).pack(side="left", padx=6)
        ttk.Checkbutton(top, text="Incluir subcarpetas", variable=self.recursive).pack(side="left", padx=6)

        src_frame = ttk.LabelFrame(self, text="Fuente de fecha (por defecto para esta carpeta)", padding=6)
        src_frame.pack(fill="x", padx=8, pady=4)
        ttk.Radiobutton(src_frame, text="EXIF, si no hay -> Fecha de modificacion", value="exif_then_mtime", variable=self.source_var).pack(side="left", padx=4)
        ttk.Radiobutton(src_frame, text="Solo EXIF", value="exif", variable=self.source_var).pack(side="left", padx=4)
        ttk.Radiobutton(src_frame, text="Solo Fecha de modificacion", value="mtime", variable=self.source_var).pack(side="left", padx=4)

        actions = ttk.Frame(self, padding=4)
        actions.pack(fill="x")
        ttk.Button(actions, text="Analizar", command=self.analyze).pack(side="left", padx=4)
        ttk.Button(actions, text="Cambiar fuente en seleccionados -> EXIF", command=lambda: self.override_selected("exif")).pack(side="left", padx=4)
        ttk.Button(actions, text="Cambiar fuente en seleccionados -> MTIME", command=lambda: self.override_selected("mtime")).pack(side="left", padx=4)
        ttk.Button(actions, text="Fecha manual...", command=self.set_manual_date).pack(side="left", padx=4)
        ttk.Button(actions, text="Copiar fecha de otro archivo...", command=self.copy_date_from_other).pack(side="left", padx=4)
        ttk.Button(actions, text="Mantener nombre actual", command=self.keep_current_name).pack(side="left", padx=4)
        ttk.Button(actions, text="Aplicar renombrado", command=self.apply).pack(side="right", padx=4)

        # Frame contenedor para tabla + scrollbar
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("file", "source", "datetime", "new_name", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended")
        for c, w in zip(cols, (380, 150, 180, 240, 140)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Permitir scroll con la rueda del mouse incluso sin foco directo en la tabla
        self.tree.bind("<MouseWheel>", lambda e: self.tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self.status = ttk.Label(self, text="Listo.", anchor="w", padding=4)
        self.status.pack(fill="x")

    def choose_folder(self):
        d = filedialog.askdirectory(title="Elegi la carpeta con fotos")
        if d:
            self.folder.set(d)

    def iter_images(self, root: Path):
        if self.recursive.get():
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in IMG_EXTS:
                    yield p
        else:
            for p in root.iterdir():
                if p.is_file() and p.suffix.lower() in IMG_EXTS:
                    yield p

    def _recompute_used_per_dir(self, excluded_iids: set):
        """Junta los nombres ya planificados por carpeta, excluyendo las filas a reasignar."""
        used_per_dir = {}
        for r in self.rows:
            if r["iid"] not in excluded_iids and r["new_name"]:
                used_per_dir.setdefault(r["path"].parent, set()).add(r["new_name"].lower())
        return used_per_dir

    def _assign_dt_to_row(self, row, dt, used_label, used_per_dir):
        """Aplica una fecha (dt) a una fila y actualiza la tabla."""
        row["datetime"] = dt
        row["used"] = used_label if dt else "-"
        if not dt:
            row["new_name"] = ""
            row["status"] = "Sin fecha disponible"
        else:
            used_set = used_per_dir.setdefault(row["path"].parent, set())
            row["new_name"] = build_new_name(dt, row["path"], used_set)
            row["status"] = "OK" if row["new_name"].lower() != row["path"].name.lower() else "Ya tiene ese nombre"
        self.tree.item(row["iid"], values=(
            str(row["path"]),
            row["used"],
            dt.strftime(OUT_FMT) if dt else "-",
            row["new_name"],
            row["status"],
        ))

    def analyze(self):
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        folder = self.folder.get().strip()
        if not folder or not Path(folder).is_dir():
            messagebox.showwarning("Atencion", "Elegi una carpeta valida.")
            return

        default_source = self.source_var.get()
        used_per_dir = {}  # dir -> set de nombres ya planificados

        for path in self.iter_images(Path(folder)):
            dt, used = resolve_datetime(path, default_source)
            row = {
                "path": path,
                "source": default_source,
                "used": used if dt else "-",
                "datetime": dt,
                "new_name": "",
                "status": "",
            }
            if not dt:
                row["status"] = "Sin fecha disponible"
            else:
                used_set = used_per_dir.setdefault(path.parent, set())
                row["new_name"] = build_new_name(dt, path, used_set)
                row["status"] = "OK" if row["new_name"].lower() != path.name.lower() else "Ya tiene ese nombre"
            self.rows.append(row)
            iid = self.tree.insert("", "end", values=(
                str(path),
                row["used"],
                dt.strftime(OUT_FMT) if dt else "-",
                row["new_name"],
                row["status"],
            ))
            row["iid"] = iid

        self.status.config(text=f"Analizados: {len(self.rows)} archivos.")

    def override_selected(self, new_source: str):
        if not self.rows:
            return
        sel = set(self.tree.selection())
        if not sel:
            messagebox.showinfo("Info", "Seleccioná filas en la tabla primero.")
            return

        used_per_dir = self._recompute_used_per_dir(excluded_iids=sel)
        for r in self.rows:
            if r["iid"] in sel:
                r["source"] = new_source
                dt, used = resolve_datetime(r["path"], new_source)
                self._assign_dt_to_row(r, dt, used if dt else "-", used_per_dir)

    def set_manual_date(self):
        sel = set(self.tree.selection())
        if not sel:
            messagebox.showinfo("Info", "Selecciona filas en la tabla primero.")
            return

        # Si hay una sola fila seleccionada y ya tiene fecha, la usamos como valor inicial
        initial = None
        if len(sel) == 1:
            for r in self.rows:
                if r["iid"] in sel and r["datetime"]:
                    initial = r["datetime"]
                    break

        dlg = ManualDateDialog(self, initial)
        self.wait_window(dlg)
        if dlg.result is None:
            return

        manual_dt, keep_time = dlg.result
        used_per_dir = self._recompute_used_per_dir(excluded_iids=sel)
        # Ordenamos por nombre original para que los sufijos _1, _2 sean predecibles
        selected_rows = sorted(
            [r for r in self.rows if r["iid"] in sel],
            key=lambda r: r["path"].name.lower()
        )

        rows_without_time = []
        for r in selected_rows:
            r["source"] = "manual"
            if keep_time:
                # Conservamos la hora original del archivo, pero usamos la fecha manual
                original_dt = r["datetime"]
                if original_dt is None:
                    # Si no habia fecha previa, intentamos obtenerla de EXIF/MTIME
                    original_dt, _ = resolve_datetime(r["path"], "exif_then_mtime")

                if original_dt is None:
                    # Sin hora disponible: marcamos como problema y seguimos
                    rows_without_time.append(r["path"].name)
                    self._assign_dt_to_row(r, None, "MANUAL (sin hora original)", used_per_dir)
                    continue

                combined = manual_dt.replace(
                    hour=original_dt.hour,
                    minute=original_dt.minute,
                    second=original_dt.second,
                )
                self._assign_dt_to_row(r, combined, "MANUAL (fecha) + hora original", used_per_dir)
            else:
                self._assign_dt_to_row(r, manual_dt, "MANUAL", used_per_dir)

        msg = f"Fecha manual aplicada a {len(selected_rows)} archivo(s)."
        if rows_without_time:
            msg += f" {len(rows_without_time)} sin hora original disponible."
        self.status.config(text=msg)

    def keep_current_name(self):
        """Marca las filas seleccionadas para que NO se renombren."""
        sel = set(self.tree.selection())
        if not sel:
            messagebox.showinfo("Info", "Selecciona filas en la tabla primero.")
            return

        count = 0
        for r in self.rows:
            if r["iid"] in sel:
                r["source"] = "keep"
                r["new_name"] = ""
                r["status"] = "Sin cambios"
                r["used"] = "-"
                # Mantenemos r["datetime"] por si despues el usuario quiere volver a procesarlo
                self.tree.item(r["iid"], values=(
                    str(r["path"]),
                    "-",
                    r["datetime"].strftime(OUT_FMT) if r["datetime"] else "-",
                    "",
                    "Sin cambios",
                ))
                count += 1

        self.status.config(text=f"{count} archivo(s) marcados para mantener nombre actual.")

    def copy_date_from_other(self):
        sel = set(self.tree.selection())
        if not sel:
            messagebox.showinfo("Info", "Selecciona filas destino en la tabla primero.")
            return

        # Todas las seleccionadas tienen que estar en la misma carpeta
        selected_rows = [r for r in self.rows if r["iid"] in sel]
        parents = {r["path"].parent for r in selected_rows}
        if len(parents) > 1:
            messagebox.showwarning(
                "Carpetas distintas",
                "Las filas seleccionadas estan en carpetas diferentes.\n"
                "Para copiar fecha de otro archivo, todas las seleccionadas deben estar en la misma carpeta."
            )
            return

        target_dir = parents.pop()

        # Candidatos: archivos de la misma carpeta, excluyendo las filas destino
        candidates = []
        for r in self.rows:
            if r["path"].parent == target_dir and r["iid"] not in sel:
                candidates.append((r["path"].name, r["datetime"], r["path"]))

        if not candidates:
            messagebox.showinfo("Sin candidatos", "No hay otros archivos analizados en esa carpeta.")
            return

        # Ordenamos los candidatos por nombre para que sea facil encontrarlos
        candidates.sort(key=lambda c: c[0].lower())

        dlg = PickSourceFileDialog(self, candidates)
        self.wait_window(dlg)
        if dlg.result is None:
            return

        dt, source_path = dlg.result
        used_per_dir = self._recompute_used_per_dir(excluded_iids=sel)
        selected_rows.sort(key=lambda r: r["path"].name.lower())
        for r in selected_rows:
            r["source"] = "copied"
            self._assign_dt_to_row(r, dt, f"COPIADA de {source_path.name}", used_per_dir)

        self.status.config(text=f"Fecha copiada a {len(selected_rows)} archivo(s) desde {source_path.name}.")

    def apply(self):
        to_rename = [r for r in self.rows if r["new_name"] and r["status"] == "OK"]
        if not to_rename:
            messagebox.showinfo("Nada para hacer", "No hay archivos validos para renombrar.")
            return
        if not messagebox.askyesno("Confirmar", f"Se van a renombrar {len(to_rename)} archivos. Continuar?"):
            return

        log_path = Path(self.folder.get()) / f"_rename_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        ok, fail = 0, 0
        with open(log_path, "w", encoding="utf-8") as log:
            log.write("original,nuevo,resultado\n")
            for r in to_rename:
                src = r["path"]
                dst = src.parent / r["new_name"]
                try:
                    if dst.exists() and dst.resolve() != src.resolve():
                        raise FileExistsError(f"Destino ya existe: {dst}")
                    src.rename(dst)
                    ok += 1
                    log.write(f'"{src}","{dst}",OK\n')
                    self.tree.item(r["iid"], values=(
                        str(dst), r["used"],
                        r["datetime"].strftime(OUT_FMT),
                        r["new_name"], "Renombrado"
                    ))
                    r["path"] = dst
                    r["status"] = "Renombrado"
                except Exception as e:
                    fail += 1
                    log.write(f'"{src}","{dst}",ERROR: {e}\n')
                    self.tree.item(r["iid"], values=(
                        str(src), r["used"],
                        r["datetime"].strftime(OUT_FMT),
                        r["new_name"], f"Error: {e}"
                    ))

        self.status.config(text=f"Hecho. OK: {ok}, errores: {fail}. Log: {log_path}")
        messagebox.showinfo("Listo", f"Renombrados: {ok}\nErrores: {fail}\nLog en:\n{log_path}")


if __name__ == "__main__":
    App().mainloop()
