"""Editor de una semana: tabla con todas las iniciativas.

Muestra las últimas semanas que existan en la base de datos (solo lectura) y,
a la derecha, una columna editable con las horas de la semana elegida.
Los cambios quedan pendientes hasta pulsar Guardar.

Lo usan "Ingresar horas" (semana actual) y "Modificar semana" (cualquier semana).
"""

import sqlite3
import time
import tkinter as tk
from datetime import date
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from catalogo import INICIATIVAS, TOPE_DEFECTO
from utils import (a_numero, etiqueta_semana, fmt_horas, lunes_de,
                   numero_semana)

N_HIST = 4                      # semanas anteriores que se muestran como contexto
COL_CODIGO, COL_NOMBRE = 0, 1


class EditorSemana(ttk.Frame):
    def __init__(self, parent, ctx, semana: date, n_hist: int = N_HIST, al_guardar=None):
        super().__init__(parent)
        self.ctx = ctx
        self.semana = semana
        self.n_hist = n_hist
        self.al_guardar = al_guardar      # función opcional que se llama tras guardar

        self.hist: list[date] = []        # semanas anteriores mostradas
        self.datos: dict = {}             # {(lunes, codigo): horas} tal como está en la BD
        self.pendientes: dict = {}        # {codigo: horas | None} cambios sin guardar
        self.col_edit = 2                 # índice de la columna editable
        self.tabla = None
        self._editor = None               # celda que se está editando en este momento
        self._total_actual = 0.0

        self.var_titulo = tk.StringVar()
        self.var_tope = tk.StringVar(value=str(TOPE_DEFECTO))
        self.var_resumen = tk.StringVar()
        self.var_totales = tk.StringVar()
        self.var_estado = tk.StringVar()
        self.var_cambios = tk.StringVar()
        self._construir()

    # -- Construcción de la interfaz --

    def _construir(self):
        ttk.Label(self, textvariable=self.var_titulo,
                  font=("Segoe UI", 14, "bold")).pack(anchor=W, pady=(0, 8))

        barra = ttk.Frame(self)
        barra.pack(fill=X, pady=(0, 8))
        ttk.Label(barra, text="Tope de horas por semana:").pack(side=LEFT)
        ttk.Entry(barra, textvariable=self.var_tope, width=6, justify=RIGHT).pack(
            side=LEFT, padx=(6, 20))
        self.lbl_resumen = ttk.Label(barra, textvariable=self.var_resumen,
                                     font=("Segoe UI", 11, "bold"))
        self.lbl_resumen.pack(side=LEFT)

        self.progreso = ttk.Progressbar(self, maximum=100, bootstyle=INFO)
        self.progreso.pack(fill=X, pady=(0, 12))

        self.contenedor = ttk.Frame(self)          # aquí vive la tabla
        self.contenedor.pack(fill=BOTH, expand=YES)

        ttk.Label(self, textvariable=self.var_totales,
                  font=("Segoe UI", 10, "bold")).pack(anchor=W, pady=(8, 0))

        info = ttk.Frame(self)
        info.pack(fill=X, pady=(4, 0))
        ttk.Label(info, text="Doble clic en la última columna  ·  Enter/↓ siguiente  ·  "
                             "↑ anterior  ·  Esc cancela", bootstyle=SECONDARY).pack(side=LEFT)
        self.lbl_estado = ttk.Label(info, textvariable=self.var_estado, bootstyle=SUCCESS)
        self.lbl_estado.pack(side=RIGHT)
        self.lbl_cambios = ttk.Label(info, textvariable=self.var_cambios, bootstyle=WARNING)
        self.lbl_cambios.pack(side=RIGHT, padx=(0, 14))

        pie = ttk.Frame(self)
        pie.pack(fill=X, pady=(10, 0))
        self.btn_guardar = ttk.Button(pie, text="Guardar  (Ctrl+S)", bootstyle=SUCCESS,
                                      command=self.guardar, state=DISABLED)
        self.btn_guardar.pack(side=LEFT)
        self.btn_descartar = ttk.Button(pie, text="Descartar cambios", state=DISABLED,
                                        bootstyle=f"{SECONDARY}-{OUTLINE}",
                                        command=self.descartar)
        self.btn_descartar.pack(side=LEFT, padx=8)
        ttk.Button(pie, text="Vaciar semana", bootstyle=f"{SECONDARY}-{OUTLINE}",
                   command=self.limpiar_semana).pack(side=LEFT)

        self.var_tope.trace_add("write", lambda *_: self._mostrar_resumen())

    def _reconstruir_tabla(self):
        if self.tabla is not None:
            self.tabla.destroy()

        es_actual = self.semana == lunes_de(date.today())
        coldata = [
            {"text": "Código", "width": 90},
            {"text": "Iniciativa", "width": 270},
            *[{"text": etiqueta_semana(s), "width": 120, "anchor": E} for s in self.hist],
            {"text": f"{'Actual' if es_actual else 'Editar'} · {etiqueta_semana(self.semana)}",
             "width": 165, "anchor": E},
        ]
        self.tabla = ttk.Tableview(
            self.contenedor, coldata=coldata, rowdata=[],
            searchable=True, yscrollbar=True, autoalign=False,
            bootstyle=SUCCESS, stripecolor=("#f2f4f5", None),
            height=12, disable_right_click=True,
        )
        self.tabla.pack(fill=BOTH, expand=YES)

        tv = self.tabla.view
        tv.tag_configure("error", foreground="#c0392b")
        tv.bind("<Double-Button-1>", self._doble_clic, "+")
        tv.bind("<MouseWheel>", lambda e: self._cerrar_editor(True), "+")
        tv.bind("<Control-s>", lambda e: self.guardar())
        self.tabla.ybar.bind("<ButtonPress-1>", lambda e: self._cerrar_editor(True), "+")

        for codigo, nombre in INICIATIVAS.items():
            valores = [codigo, nombre]
            valores += [fmt_horas(self.datos.get((s, codigo))) for s in self.hist]
            valores.append(fmt_horas(self._efectivo(codigo)))
            self.tabla.insert_row(END, values=valores, reload=False)
        self.tabla.load_table_data()

    # -- Carga de datos --

    def recargar(self):
        """Vuelve a leer la BD y redibuja la tabla. Descarta lo que esté pendiente."""
        self._abandonar_editor()
        self.pendientes.clear()
        repo, usuario = self.ctx.repo, self.ctx.usuario
        # Las últimas N semanas que existan en la BD antes de la que se edita
        self.hist = repo.semanas_registradas(usuario, antes_de=self.semana, n=self.n_hist)
        self.datos = repo.cargar(usuario, self.hist + [self.semana])
        self.col_edit = 2 + len(self.hist)

        prefijo = "Semana actual" if self.semana == lunes_de(date.today()) else "Semana"
        self.var_titulo.set(f"{prefijo}  ·  {etiqueta_semana(self.semana)}")
        self.var_estado.set("")
        self._reconstruir_tabla()
        self.revisar()

    def _efectivo(self, codigo):
        """Valor que se ve en la celda: el pendiente si lo hay, si no el guardado."""
        if codigo in self.pendientes:
            return self.pendientes[codigo]
        return self.datos.get((self.semana, codigo))

    # -- Edición directa sobre la celda --

    def _doble_clic(self, event):
        tv = self.tabla.view
        if tv.identify_region(event.x, event.y) != "cell":
            return
        iid = tv.identify_row(event.y)
        columna = int(tv.identify_column(event.x)[1:]) - 1
        if iid and columna == self.col_edit:       # solo se escribe en la columna editable
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
        bbox = tv.bbox(iid, f"#{self.col_edit + 1}")
        if not bbox:
            return
        x, y, w, h = bbox

        original = str(fila.values[self.col_edit])
        var = tk.StringVar(value=original)
        entry = ttk.Entry(tv, textvariable=var, justify=RIGHT)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, END)
        entry.icursor(END)

        self._editor = {"entry": entry, "fila": fila, "var": var, "original": original}

        var.trace_add("write", lambda *_: self._escribir_en_vivo())   # total en vivo
        for tecla in ("<Return>", "<KP_Enter>", "<Down>", "<Tab>"):
            entry.bind(tecla, lambda e: self._mover(+1))
        for tecla in ("<Up>", "<Shift-Tab>"):
            entry.bind(tecla, lambda e: self._mover(-1))
        entry.bind("<Control-s>", lambda e: (self.guardar(), "break")[1])
        entry.bind("<Escape>", lambda e: self._cerrar_editor(False))
        entry.bind("<FocusOut>", lambda e: self._cerrar_editor(True))

    def _mover(self, delta):
        """Confirma la celda y abre la de la fila siguiente (+1) o anterior (-1)."""
        ed = self._editor
        if not ed:
            return "break"
        iid = ed["fila"].iid
        self._cerrar_editor(True)
        hijos = self.tabla.view.get_children()     # solo las filas visibles (respeta el filtro)
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

    def _abandonar_editor(self):
        """Cierra el campo de texto sin aplicar nada (se usa al recargar)."""
        ed, self._editor = self._editor, None
        if ed:
            ed["entry"].destroy()

    # -- Cambios pendientes y guardado --

    def _aplicar(self, fila, texto, final):
        codigo = fila.values[COL_CODIGO]
        valores = list(fila.values)

        if not final:                 # mientras escribes: solo se muestra, aún no es un cambio
            valores[self.col_edit] = texto
            fila.values = valores
            self.revisar()
            return

        horas = a_numero(texto)
        if horas is None:             # texto inválido: se descarta y vuelve el valor anterior
            valores[self.col_edit] = fmt_horas(self._efectivo(codigo))
            self._estado(f"No se aplicó: «{texto.strip()}» no es un número válido", error=True)
        else:
            nuevo = horas if texto.strip() else None
            if nuevo != self._efectivo(codigo):
                self.var_estado.set("")
            if nuevo == self.datos.get((self.semana, codigo)):
                self.pendientes.pop(codigo, None)      # volvió al valor guardado: ya no es cambio
            else:
                self.pendientes[codigo] = nuevo
            valores[self.col_edit] = fmt_horas(nuevo)

        fila.values = valores
        self.revisar()

    def guardar(self) -> bool:
        """Graba todos los cambios pendientes en una sola operación."""
        self._cerrar_editor(True)
        if not self.pendientes:
            return True
        try:
            self.ctx.repo.guardar_semana(self.ctx.usuario, self.semana, self.pendientes)
        except sqlite3.Error as error:
            self._estado("Error al guardar: no se grabó nada", error=True)
            messagebox.showerror("Error al guardar", str(error))
            return False

        for codigo, horas in self.pendientes.items():
            if horas is None:
                self.datos.pop((self.semana, codigo), None)
            else:
                self.datos[(self.semana, codigo)] = horas
        self.pendientes.clear()
        self._estado(f"Guardado ✓ {time.strftime('%H:%M:%S')}")
        self._actualizar_botones()
        if self.al_guardar:
            self.al_guardar()
        return True

    def descartar(self):
        self._cerrar_editor(True)
        if not self.pendientes:
            return
        if messagebox.askyesno("Descartar cambios",
                               f"¿Descartar los {len(self.pendientes)} cambios sin guardar?"):
            self.recargar()
            self._estado("Cambios descartados")

    def limpiar_semana(self):
        """Deja vacía toda la semana. Como cualquier cambio, se aplica al pulsar Guardar."""
        self._cerrar_editor(True)
        if not messagebox.askyesno(
                "Vaciar semana",
                f"¿Vaciar todas las horas de {etiqueta_semana(self.semana)}?\n"
                "Se aplicará cuando pulses Guardar."):
            return
        for fila in self.tabla.tablerows:
            self._aplicar(fila, "", final=True)

    def puede_salir(self) -> bool:
        """Si hay cambios sin guardar, pregunta qué hacer. False = el usuario canceló."""
        self._cerrar_editor(True)
        if not self.pendientes:
            return True
        n = len(self.pendientes)
        respuesta = messagebox.askyesnocancel(
            "Cambios sin guardar",
            f"Tienes {n} cambio{'s' if n != 1 else ''} sin guardar en "
            f"{etiqueta_semana(self.semana)}.\n\n¿Guardar antes de salir?")
        if respuesta is None:          # Cancelar: se queda donde está
            return False
        if respuesta:                  # Sí: guarda (si falla, tampoco sale)
            return self.guardar()
        self.pendientes.clear()        # No: descarta
        return True

    # -- Validación y totales --

    def revisar(self):
        """Marca en rojo las horas inválidas y recalcula el total de la semana."""
        total = 0.0
        for fila in self.tabla.tablerows:
            horas = a_numero(fila.values[self.col_edit])
            self._poner_estado(fila, "error" if horas is None else None)
            total += horas or 0.0
        self._total_actual = total
        self._mostrar_resumen()
        self._mostrar_totales()
        self._actualizar_botones()

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
        semana = f"S{numero_semana(self.semana)}"

        if not tope:
            self.var_resumen.set("Define un tope válido")
            self.lbl_resumen.configure(bootstyle=DANGER)
            self.progreso.configure(value=0, bootstyle=DANGER)
            return

        disponible = tope - total
        if disponible < 0:
            texto = f"{semana}: {total:g} / {tope:g} h  |  Excedido por {-disponible:g} h"
            estilo = DANGER
        elif disponible == 0:
            texto = f"{semana}: {total:g} / {tope:g} h  |  Tope completo"
            estilo = SUCCESS
        else:
            texto = f"{semana}: {total:g} / {tope:g} h  |  Disponible: {disponible:g} h"
            estilo = INFO

        self.var_resumen.set(texto)
        self.lbl_resumen.configure(bootstyle=estilo)
        self.progreso.configure(value=min(total / tope * 100, 100), bootstyle=estilo)

    def _mostrar_totales(self):
        partes = []
        for semana in self.hist:
            total = sum(h for (s, c), h in self.datos.items() if s == semana and c in INICIATIVAS)
            partes.append(f"S{numero_semana(semana)}: {total:g} h")
        partes.append(f"S{numero_semana(self.semana)} (esta): {self._total_actual:g} h")
        self.var_totales.set("Totales  ·  " + "   |   ".join(partes))

    def _actualizar_botones(self):
        n = len(self.pendientes)
        estado = NORMAL if n else DISABLED
        self.btn_guardar.configure(state=estado)
        self.btn_descartar.configure(state=estado)
        self.var_cambios.set(f"● {n} cambio{'s' if n != 1 else ''} sin guardar" if n else "")

    def _estado(self, texto, error=False):
        self.var_estado.set(texto)
        self.lbl_estado.configure(bootstyle=DANGER if error else SUCCESS)
