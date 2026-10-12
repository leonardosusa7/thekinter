import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from base import Modulo
from catalogo import INICIATIVAS
from utils import matriz_historico

OPCIONES = {
    "Últimas 4 semanas": 4,
    "Últimas 8 semanas": 8,
    "Últimas 12 semanas": 12,
    "Últimas 26 semanas": 26,
    "Todas": None,
}


class VerHistorico(Modulo):
    """Consulta de todas las semanas registradas (solo lectura)."""

    nombre = "Ver histórico"

    def construir(self):
        self.var_resumen = tk.StringVar()

        barra = ttk.Frame(self)
        barra.pack(fill=X, pady=(0, 12))
        ttk.Label(barra, text="Histórico de horas",
                  font=("Segoe UI", 14, "bold")).pack(side=LEFT)
        ttk.Button(barra, text="Actualizar", bootstyle=f"{SECONDARY}-{OUTLINE}",
                   command=self.cargar).pack(side=RIGHT)
        self.combo = ttk.Combobox(barra, state="readonly", width=20, values=list(OPCIONES))
        self.combo.set("Últimas 12 semanas")
        self.combo.pack(side=RIGHT, padx=(0, 10))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.cargar())
        ttk.Label(barra, text="Mostrar:").pack(side=RIGHT, padx=(0, 6))

        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(fill=BOTH, expand=YES)
        ttk.Label(self, textvariable=self.var_resumen,
                  font=("Segoe UI", 10, "bold")).pack(anchor=W, pady=(8, 0))
        ttk.Label(self, text="La semana más reciente va primero; desplázate a la derecha "
                             "para ver las anteriores.", bootstyle=SECONDARY).pack(anchor=W)

    def al_mostrar(self):
        self.cargar()

    def cargar(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

        semanas = self.ctx.repo.semanas_registradas(self.ctx.usuario)
        limite = OPCIONES.get(self.combo.get())
        if limite:
            semanas = semanas[-limite:]
        if not semanas:
            ttk.Label(self.contenedor, bootstyle=SECONDARY,
                      text="Aún no hay horas registradas. Empieza en «Ingresar horas».",
                      ).pack(anchor=W)
            self.var_resumen.set("")
            return

        semanas = semanas[::-1]                      # la más reciente primero
        datos = self.ctx.repo.cargar(self.ctx.usuario, semanas)
        encabezados, filas, totales = matriz_historico(datos, semanas, INICIATIVAS)

        coldata = [
            {"text": "Código", "width": 90},
            {"text": "Iniciativa", "width": 270},
            *[{"text": texto, "width": 175, "anchor": E} for texto in encabezados],
            {"text": "Total", "width": 90, "anchor": E},
        ]
        tabla = ttk.Tableview(
            self.contenedor, coldata=coldata, rowdata=filas,
            searchable=True, yscrollbar=True, autoalign=False,
            bootstyle=SUCCESS, stripecolor=("#f2f4f5", None),
            height=14, disable_right_click=True,
        )
        tabla.pack(fill=BOTH, expand=YES)

        total = sum(totales)
        self.var_resumen.set(
            f"{len(semanas)} semana{'s' if len(semanas) != 1 else ''}  ·  {total:g} h en total  ·  "
            f"promedio {total / len(semanas):.1f} h por semana")
