import sqlite3
import time
import tkinter as tk
from datetime import timedelta
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from catalogo import INICIATIVAS, TOPE_DEFECTO
from db import RegistroHoras

N_HIST = 4                      # semanas anteriores que se muestran
COL_CODIGO, COL_NOMBRE = 0, 1
COL_ACTUAL = 2 + N_HIST         # última columna: semana actual (la única editable)

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def a_numero(texto) -> float | None:
    """Convierte '7,5' o '7.5' en float. Vacío = 0. Inválido = None."""
    texto = str(texto).strip().replace(",", ".")
    if not texto:
        return 0.0
    try:
        valor = float(texto)
    except ValueError:
        return None
    return valor if valor >= 0 else None


def numero_semana(lunes) -> int:
    return lunes.isocalendar()[1]


def rango_semana(lunes) -> str:
    """'5-11 oct' o, si cruza de mes, '28 sep-4 oct'."""
    fin = lunes + timedelta(days=6)
    if lunes.month == fin.month:
        return f"{lunes.day}-{fin.day} {MESES[fin.month - 1]}"
    return f"{lunes.day} {MESES[lunes.month - 1]}-{fin.day} {MESES[fin.month - 1]}"


def etiqueta_semana(lunes) -> str:
    return f"S{numero_semana(lunes)} · {rango_semana(lunes)}"


class ModuloHoras(ttk.Frame):
    def __init__(self, parent, usuario, repo=None):
        super().__init__(parent, padding=15)
        self.usuario = usuario
        self.repo = repo or RegistroHoras()
        self.semanas = ultimas_semanas(N_HIST + 1)       # 4 anteriores + la actual
        self.semana_actual = self.semanas[-1]

        # Fuente de verdad: {(lunes, codigo): horas}
        self.datos = self.repo.cargar(usuario, self.semanas)
        self.totales_hist = [
            sum(h for (s, c), h in self.datos.items() if s == semana and c in INICIATIVAS)
            for semana in self.semanas[:-1]
        ]

        self.var_tope = tk.StringVar(value=str(TOPE_DEFECTO))
        self.var_resumen = tk.StringVar()
        self.var_totales = tk.StringVar()
        self.var_estado = tk.StringVar()
        self._editor = None          # celda que se está editando en este momento
        self._total_actual = 0.0

        self._construir_resumen()
        self._construir_tabla()
        self._llenar_tabla()

        self.var_tope.trace_add("write", lambda *_: self._mostrar_resumen())
        self.revisar()

    # -- Construcción de la interfaz --

    def _construir_resumen(self):
        barra = ttk.Frame(self)
        barra.pack(fill=X, pady=(0, 8))

        ttk.Label(barra, text="Tope de horas por semana:").pack(side=LEFT)
        ttk.Entry(barra, textvariable=self.var_tope, width=6, justify=RIGHT).pack(
            side=LEFT, padx=(6, 20)
        )
        self.lbl_resumen = ttk.Label(
            barra, textvariable=self.var_resumen, font=("Segoe UI", 11, "bold")
        )
        self.lbl_resumen.pack(side=LEFT)

        self.progreso = ttk.Progressbar(self, maximum=100, bootstyle=INFO)
        self.progreso.pack(fill=X, pady=(0, 12))

    def _construir_tabla(self):
        coldata = [
            {"text": "Código", "width": 90},
            {"text": "Iniciativa", "width": 270},
            *[{"text": etiqueta_semana(s), "width": 120, "anchor": E}
              for s in self.semanas[:-1]],
            {"text": f"Actual · {etiqueta_semana(self.semana_actual)}",
             "width": 160, "anchor": E},
        ]
        self.tabla = ttk.Tableview(
            self,
            coldata=coldata,
            rowdata=[],
            searchable=True,
            yscrollbar=True,
            autoalign=False,
            bootstyle=SUCCESS,
            stripecolor=("#f2f4f5", None),
            height=12,
            disable_right_click=True,
        )
        self.tabla.pack(fill=BOTH, expand=YES)

        tv = self.tabla.view
        tv.tag_configure("error", foreground="#c0392b")
        tv.bind("<Double-Button-1>", self._doble_clic, "+")
        tv.bind("<MouseWheel>", lambda e: self._cerrar_editor(True), "+")
        self.tabla.ybar.bind("<ButtonPress-1>", lambda e: self._cerrar_editor(True), "+")

        ttk.Label(
            self, textvariable=self.var_totales, font=("Segoe UI", 10, "bold")
        ).pack(anchor=W, pady=(8, 0))

        info = ttk.Frame(self)
        info.pack(fill=X, pady=(4, 0))
        ttk.Label(
            info,
            text="Doble clic en la última columna para escribir  ·  "
                 "Enter o ↓ siguiente  ·  ↑ anterior  ·  Esc cancela",
            bootstyle=SECONDARY,
        ).pack(side=LEFT)
        self.lbl_estado = ttk.Label(info, textvariable=self.var_estado, bootstyle=SUCCESS)
        self.lbl_estado.pack(side=RIGHT)

        pie = ttk.Frame(self)
        pie.pack(fill=X, pady=(10, 0))
        ttk.Button(
            pie, text="Limpiar semana actual", bootstyle=(SECONDARY, OUTLINE),
            command=self.limpiar_semana,
        ).pack(side=LEFT)

    def _llenar_tabla(self):
        for codigo, nombre in INICIATIVAS.items():
            valores = [codigo, nombre] + [
                self._fmt(self.datos.get((semana, codigo))) for semana in self.semanas
            ]
            self.tabla.insert_row(END, values=valores, reload=False)
        self.tabla.load_table_data()

    @staticmethod
    def _fmt(horas) -> str:
        return "" if horas is None else f"{horas:g}"

    # -- Edición directa sobre la celda --

    def _doble_clic(self, event):
        tv = self.tabla.view
        if tv.identify_region(event.x, event.y) != "cell":
            return
        iid = tv.identify_row(event.y)
        columna = int(tv.identify_column(event.x)[1:]) - 1
        if iid and columna == COL_ACTUAL:       # solo se escribe en la semana actual
            self._editar_celda(iid)

    def _editar_celda(self, iid):
        """Coloca un campo de texto encima de la celda para escribir ahí mismo."""
        self._cerrar_editor(True)
        tv = self.tabla.view
        fila = self.tabla.iidmap.get(iid)
        if fila is None:
            return
        try:
            tv.see(iid)
        except tk.TclError:
            return
        self.update_idletasks()
        bbox = tv.bbox(iid, f"#{COL_ACTUAL + 1}")
        if not bbox:
            return
        x, y, w, h = bbox

        original = str(fila.values[COL_ACTUAL])
        var = tk.StringVar(value=original)
        entry = ttk.Entry(tv, textvariable=var, justify=RIGHT)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, END)
        entry.icursor(END)

        self._editor = {"entry": entry, "fila": fila, "var": var, "original": original}

        # Mientras escribes, el total se actualiza en vivo
        var.trace_add("write", lambda *_: self._escribir_en_vivo())
        for tecla in ("<Return>", "<KP_Enter>", "<Down>", "<Tab>"):
            entry.bind(tecla, lambda e: self._mover(+1))
        for tecla in ("<Up>", "<Shift-Tab>"):
            entry.bind(tecla, lambda e: self._mover(-1))
        entry.bind("<Escape>", lambda e: self._cerrar_editor(False))
        entry.bind("<FocusOut>", lambda e: self._cerrar_editor(True))

    def _mover(self, delta):
        """Confirma la celda y abre la de la fila siguiente (+1) o anterior (-1)."""
        ed = self._editor
        if not ed:
            return "break"
        iid = ed["fila"].iid
        self._cerrar_editor(True)
        hijos = self.tabla.view.get_children()     # solo las filas visibles (con filtro)
        if iid in hijos:
            pos = hijos.index(iid) + delta
            if 0 <= pos < len(hijos):
                destino = hijos[pos]
                self.after(20, lambda: self._editar_celda(destino))
        return "break"

    def _escribir_en_vivo(self):
        ed = self._editor
        if ed:
            self._aplicar(ed["fila"], ed["var"].get(), final=False)

    def _cerrar_editor(self, guardar=True):
        ed = self._editor
        if not ed:
            return
        self._editor = None      # primero se limpia, así un segundo cierre no hace nada
        texto = ed["var"].get() if guardar else ed["original"]
        ed["entry"].destroy()
        self._aplicar(ed["fila"], texto, final=True)

    # -- Guardado y validación --

    def _aplicar(self, fila, texto, final):
        codigo = fila.values[COL_CODIGO]
        valores = list(fila.values)

        if not final:                 # mientras escribes: solo se muestra, no se guarda
            valores[COL_ACTUAL] = texto
            fila.values = valores
            self.revisar()
            return

        clave = (self.semana_actual, codigo)
        horas = a_numero(texto)
        if horas is None:             # texto inválido: se descarta y vuelve el valor guardado
            valores[COL_ACTUAL] = self._fmt(self.datos.get(clave))
            self._estado(f"No se guardó: «{texto.strip()}» no es un número válido", error=True)
        else:
            nuevo = horas if texto.strip() else None
            if nuevo != self.datos.get(clave) and not self._guardar(codigo, nuevo):
                nuevo = self.datos.get(clave)       # falló el guardado: se conserva lo anterior
            valores[COL_ACTUAL] = self._fmt(nuevo)

        fila.values = valores
        self.revisar()

    def _guardar(self, codigo, horas) -> bool:
        try:
            self.repo.guardar(self.usuario, self.semana_actual, codigo, horas)
        except sqlite3.Error as error:
            self._estado("Error al guardar", error=True)
            messagebox.showerror("Error al guardar", str(error))
            return False
        clave = (self.semana_actual, codigo)
        if horas is None:
            self.datos.pop(clave, None)
        else:
            self.datos[clave] = horas
        self._estado(f"Guardado ✓ {time.strftime('%H:%M:%S')}")
        return True

    def _estado(self, texto, error=False):
        self.var_estado.set(texto)
        self.lbl_estado.configure(bootstyle=DANGER if error else SUCCESS)

    # -- Totales --

    def revisar(self):
        """Marca en rojo las horas inválidas y recalcula el total de la semana actual."""
        total = 0.0
        for fila in self.tabla.tablerows:
            horas = a_numero(fila.values[COL_ACTUAL])
            self._poner_estado(fila, "error" if horas is None else None)
            total += horas or 0.0
        self._total_actual = total
        self._mostrar_resumen()
        self._mostrar_totales()

    def _poner_estado(self, fila, estado):
        tv = self.tabla.view
        try:
            tags = tv.item(fila.iid, "tags")
            tags = tags.split() if isinstance(tags, str) else list(tags)
            tags = [t for t in tags if t != "error"]
            if estado:
                tags.append(estado)
            tv.item(fila.iid, tags=tags)
        except tk.TclError:
            pass   # la fila todavía no está dibujada

    def _mostrar_resumen(self):
        total = self._total_actual
        tope = a_numero(self.var_tope.get())

        if not tope:
            self.var_resumen.set("Define un tope válido")
            self.lbl_resumen.configure(bootstyle=DANGER)
            self.progreso.configure(value=0, bootstyle=DANGER)
            return

        disponible = tope - total
        if disponible < 0:
            texto = f"Esta semana: {total:g} / {tope:g} h  |  Excedido por {-disponible:g} h"
            estilo = DANGER
        elif disponible == 0:
            texto = f"Esta semana: {total:g} / {tope:g} h  |  Tope completo"
            estilo = SUCCESS
        else:
            texto = f"Esta semana: {total:g} / {tope:g} h  |  Disponible: {disponible:g} h"
            estilo = INFO

        self.var_resumen.set(texto)
        self.lbl_resumen.configure(bootstyle=estilo)
        self.progreso.configure(value=min(total / tope * 100, 100), bootstyle=estilo)

    def _mostrar_totales(self):
        partes = [
            f"S{numero_semana(semana)}: {total:g} h"
            for semana, total in zip(self.semanas[:-1], self.totales_hist)
        ]
        partes.append(f"S{numero_semana(self.semana_actual)} (actual): {self._total_actual:g} h")
        self.var_totales.set("Totales  ·  " + "   |   ".join(partes))

    # -- Botones --

    def limpiar_semana(self):
        self._cerrar_editor(False)
        etiqueta = etiqueta_semana(self.semana_actual)
        if not messagebox.askyesno("Limpiar", f"¿Borrar las horas de la semana actual ({etiqueta})?"):
            return
        try:
            self.repo.borrar_semana(self.usuario, self.semana_actual)
        except sqlite3.Error as error:
            messagebox.showerror("Error al guardar", str(error))
            return
        for clave in [k for k in self.datos if k[0] == self.semana_actual]:
            del self.datos[clave]
        for fila in self.tabla.tablerows:
            valores = list(fila.values)
            valores[COL_ACTUAL] = ""
            fila.values = valores
        self.revisar()
        self._estado(f"Semana actual limpiada {time.strftime('%H:%M:%S')}")

    def cerrar(self):
        """Guarda lo que se esté escribiendo y cierra la base de datos."""
        self._cerrar_editor(True)
        self.repo.cerrar()


class App(ttk.Window):
    def __init__(self, usuario):
        super().__init__(title=f"Registro de horas - {usuario}",
                         themename="flatly", size=(1040, 700))
        self.modulo = ModuloHoras(self, usuario)
        self.modulo.pack(fill=BOTH, expand=YES)
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    def _al_cerrar(self):
        self.modulo.cerrar()
        self.destroy()
