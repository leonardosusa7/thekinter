import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from base import Modulo
from editor_semana import EditorSemana
from utils import etiqueta_semana, semanas_disponibles


class ModificarSemana(Modulo):
    """Elegir una semana cualquiera y corregir sus horas."""

    nombre = "Modificar semana"

    def construir(self):
        self.editor = None
        self.mapa = {}              # texto del selector -> lunes de esa semana
        self._texto_actual = ""     # texto que corresponde a la semana abierta

        barra = ttk.Frame(self)
        barra.pack(fill=X, pady=(0, 14))
        ttk.Label(barra, text="Semana a modificar:",
                  font=("Segoe UI", 12, "bold")).pack(side=LEFT)
        self.combo = ttk.Combobox(barra, state="readonly", width=38)
        self.combo.pack(side=LEFT, padx=10)
        self.combo.bind("<<ComboboxSelected>>", self._al_elegir)

        self.lbl_vacio = ttk.Label(
            self, text="Elige una semana para ver y corregir sus horas.", bootstyle=SECONDARY)
        self.lbl_vacio.pack(anchor=W)
        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(fill=BOTH, expand=YES)

    def al_mostrar(self):
        self._actualizar_lista()
        if self.editor is not None:
            self.editor.recargar()

    def puede_salir(self):
        return self.editor.puede_salir() if self.editor is not None else True

    def _actualizar_lista(self):
        """Semanas con datos + las últimas 8 de calendario (para cargar una que se olvidó)."""
        registradas = set(self.ctx.repo.semanas_registradas(self.ctx.usuario))
        self.mapa = {}
        for semana in semanas_disponibles(registradas):
            texto = etiqueta_semana(semana)
            if semana not in registradas:
                texto += "  ·  sin registros"
            self.mapa[texto] = semana
        self.combo.configure(values=list(self.mapa))

        if self.editor is not None:
            for texto, semana in self.mapa.items():
                if semana == self.editor.semana:
                    self._texto_actual = texto
            self.combo.set(self._texto_actual)

    def _al_elegir(self, event=None):
        texto = self.combo.get()
        semana = self.mapa.get(texto)
        if semana is None:
            return
        if self.editor is not None:
            if self.editor.semana == semana:
                return
            if not self.editor.puede_salir():       # canceló: se queda en la semana anterior
                self.combo.set(self._texto_actual)
                return
            self.editor.destroy()

        self.lbl_vacio.pack_forget()
        self.editor = EditorSemana(self.contenedor, self.ctx, semana,
                                   al_guardar=self._actualizar_lista)
        self.editor.pack(fill=BOTH, expand=YES)
        self.editor.recargar()
        self._texto_actual = texto
