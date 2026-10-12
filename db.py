"""Acceso a datos: guarda y lee las horas por usuario, semana e iniciativa.

No contiene nada de interfaz, así que se puede probar sin abrir ventanas.
Usa SQLite, que ya viene con Python. El archivo se crea solo la primera vez.

Para llenar datos de prueba (por defecto, 8 semanas anteriores a la actual):
    python db.py --demo admin
    python db.py --demo admin 12      # 12 semanas
"""

import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from utils import lunes_de

RUTA_DB = Path(__file__).with_name("registro_horas.db")


class RegistroHoras:
    def __init__(self, ruta=RUTA_DB):
        self.conn = sqlite3.connect(ruta)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS horas (
                usuario TEXT NOT NULL,
                semana  TEXT NOT NULL,   -- lunes de la semana, formato AAAA-MM-DD
                codigo  TEXT NOT NULL,
                horas   REAL NOT NULL,
                PRIMARY KEY (usuario, semana, codigo)
            )
            """
        )
        self.conn.commit()

    def semanas_registradas(self, usuario: str, antes_de: date | None = None,
                            n: int | None = None) -> list[date]:
        """Semanas (lunes) que tienen datos, de la más antigua a la más reciente.

        antes_de: solo semanas anteriores a esa fecha.
        n: solo las `n` más recientes.
        """
        sql = "SELECT DISTINCT semana FROM horas WHERE usuario = ?"
        params: list = [usuario]
        if antes_de is not None:
            sql += " AND semana < ?"
            params.append(antes_de.isoformat())
        sql += " ORDER BY semana DESC"
        if n is not None:
            sql += " LIMIT ?"
            params.append(n)
        filas = self.conn.execute(sql, params).fetchall()
        return sorted(date.fromisoformat(s) for (s,) in filas)

    def cargar(self, usuario: str, semanas: list[date]) -> dict[tuple[date, str], float]:
        """Devuelve {(lunes, codigo): horas} para las semanas pedidas."""
        if not semanas:
            return {}
        marcas = ",".join("?" * len(semanas))
        filas = self.conn.execute(
            f"SELECT semana, codigo, horas FROM horas "
            f"WHERE usuario = ? AND semana IN ({marcas})",
            [usuario, *[s.isoformat() for s in semanas]],
        )
        return {(date.fromisoformat(s), c): h for s, c, h in filas}

    def guardar_semana(self, usuario: str, semana: date, cambios: dict[str, float | None]):
        """Aplica varios cambios de una semana en una sola transacción.

        `cambios` es {codigo: horas}; con horas=None se borra ese registro.
        Si algo falla, no se guarda nada.
        """
        iso = semana.isoformat()
        with self.conn:
            for codigo, horas in cambios.items():
                if horas is None:
                    self.conn.execute(
                        "DELETE FROM horas WHERE usuario = ? AND semana = ? AND codigo = ?",
                        (usuario, iso, codigo),
                    )
                else:
                    self.conn.execute(
                        """
                        INSERT INTO horas (usuario, semana, codigo, horas) VALUES (?, ?, ?, ?)
                        ON CONFLICT (usuario, semana, codigo) DO UPDATE SET horas = excluded.horas
                        """,
                        (usuario, iso, codigo, horas),
                    )

    def cerrar(self):
        self.conn.close()


def sembrar_demo(repo: RegistroHoras, usuario: str, codigos: list[str],
                 semanas: int = 8, hoy: date | None = None, semilla: int | None = None):
    """Llena las `semanas` anteriores a la actual con horas aleatorias.

    Cada iniciativa recibe horas en cada semana (múltiplos de 0,5) y el total
    semanal ronda entre 34 y 44 h. La semana actual queda vacía.
    """
    azar = random.Random(semilla)
    actual = lunes_de(hoy or date.today())
    for k in range(1, semanas + 1):
        total = azar.randint(68, 88) / 2
        pesos = [azar.random() + 0.3 for _ in codigos]
        horas = [max(0.5, round(total * p / sum(pesos) * 2) / 2) for p in pesos]
        repo.guardar_semana(usuario, actual - timedelta(weeks=k), dict(zip(codigos, horas)))


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--demo":
        from catalogo import INICIATIVAS

        n = int(sys.argv[3]) if len(sys.argv) == 4 else 8
        repo = RegistroHoras()
        sembrar_demo(repo, sys.argv[2], list(INICIATIVAS), semanas=n)
        repo.cerrar()
        print(f"Datos de prueba cargados para '{sys.argv[2]}': {n} semanas en {RUTA_DB}")
    else:
        print("Uso: python db.py --demo <usuario> [semanas]")
