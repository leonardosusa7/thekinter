"""Ventana principal: menú lateral y el área donde se muestra cada módulo.

Para agregar un módulo nuevo basta con crearlo (heredando de `Modulo`) y
añadirlo a la lista MODULOS. Aquí no hay que tocar nada más.
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from base import Contexto
from db import RegistroHoras
from mod_historico import VerHistorico
from mod_ingresar import IngresarHoras
from mod_modificar import ModificarSemana

MODULOS = [IngresarHoras, VerHistorico, ModificarSemana]


class Shell(ttk.Window):
    def __init__(self, usuario):
        super().__init__(title=f"Registro de horas - {usuario}",
                         themename="flatly", size=(1120, 740))
        self.ctx = Contexto(usuario, RegistroHoras())
        self.instancias = {}        # módulos ya creados (se crean la primera vez que se abren)
        self.botones = {}
        self.actual = None
        self.clase_actual = None

        menu = ttk.Frame(self, padding=14)
        menu.pack(side=LEFT, fill=Y)
        ttk.Label(menu, text="Registro de horas",
                  font=("Segoe UI", 13, "bold")).pack(anchor=W)
        ttk.Label(menu, text=f"Usuario: {usuario}",
                  bootstyle=SECONDARY).pack(anchor=W, pady=(0, 18))
        for clase in MODULOS:
            boton = ttk.Button(menu, text=clase.nombre, width=20,
                               bootstyle=f"{SUCCESS}-{OUTLINE}",
                               command=lambda c=clase: self.mostrar(c))
            boton.pack(fill=X, pady=3)
            self.botones[clase] = boton

        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y)
        self.area = ttk.Frame(self)
        self.area.pack(side=LEFT, fill=BOTH, expand=YES)

        self.mostrar(MODULOS[0])
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    def mostrar(self, clase):
        if clase is self.clase_actual:
            return
        # Antes de cambiar, el módulo actual puede pedir que no se salga (cambios sin guardar)
        if self.actual is not None and not self.actual.puede_salir():
            return
        if self.actual is not None:
            self.actual.pack_forget()

        if clase not in self.instancias:
            self.instancias[clase] = clase(self.area, self.ctx)
        self.actual = self.instancias[clase]
        self.clase_actual = clase
        self.actual.pack(fill=BOTH, expand=YES)
        self.actual.al_mostrar()

        for c, boton in self.botones.items():
            boton.configure(bootstyle=SUCCESS if c is clase else f"{SUCCESS}-{OUTLINE}")

    def _al_cerrar(self):
        if self.actual is not None and not self.actual.puede_salir():
            return
        self.ctx.repo.cerrar()
        self.destroy()
