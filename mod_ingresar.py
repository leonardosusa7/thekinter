from datetime import date

from ttkbootstrap.constants import *

from base import Modulo
from editor_semana import EditorSemana
from utils import lunes_de


class IngresarHoras(Modulo):
    """Registrar las horas de la semana actual."""

    nombre = "Ingresar horas"

    def construir(self):
        self.editor = EditorSemana(self, self.ctx, lunes_de(date.today()))
        self.editor.pack(fill=BOTH, expand=YES)

    def al_mostrar(self):
        # Por si la app quedó abierta de una semana a otra, o se modificó algo en otro módulo
        self.editor.semana = lunes_de(date.today())
        self.editor.recargar()

    def puede_salir(self):
        return self.editor.puede_salir()
