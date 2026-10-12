"""Piezas comunes a todos los módulos de la aplicación."""

import ttkbootstrap as ttk


class Contexto:
    """Lo que comparten todos los módulos: quién es el usuario y cómo llegar a los datos."""

    def __init__(self, usuario, repo):
        self.usuario = usuario
        self.repo = repo


class Modulo(ttk.Frame):
    """Contrato de un módulo: es una pantalla con nombre que el menú puede mostrar.

    Para crear uno nuevo: heredar de esta clase, definir `nombre`, dibujar la
    interfaz en `construir()` y agregarlo a la lista MODULOS de shell.py.
    """

    nombre = "Sin nombre"

    def __init__(self, parent, ctx):
        super().__init__(parent, padding=15)
        self.ctx = ctx
        self.construir()

    def construir(self):
        """Dibuja la interfaz. Se llama una sola vez, la primera vez que se abre."""
        raise NotImplementedError

    def al_mostrar(self):
        """Se llama cada vez que el usuario entra al módulo (aquí se refrescan los datos)."""

    def puede_salir(self) -> bool:
        """El menú lo consulta antes de cambiar de módulo o cerrar. False = quedarse aquí."""
        return True
