"""Funciones puras: sin interfaz y sin base de datos, fáciles de probar.

Fechas de semana, formato de horas y armado de la matriz del histórico.
"""

from datetime import date, timedelta

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def lunes_de(dia: date) -> date:
    """Lunes de la semana a la que pertenece `dia`."""
    return dia - timedelta(days=dia.weekday())


def a_numero(texto) -> float | None:
    """Convierte '7,5' o '7.5' en float. Vacío = 0. Inválido o negativo = None."""
    texto = str(texto).strip().replace(",", ".")
    if not texto:
        return 0.0
    try:
        valor = float(texto)
    except ValueError:
        return None
    return valor if valor >= 0 else None


def fmt_horas(horas) -> str:
    """8.0 -> '8', 7.5 -> '7.5', None -> ''."""
    return "" if horas is None else f"{horas:g}"


def numero_semana(lunes: date) -> int:
    return lunes.isocalendar()[1]


def rango_semana(lunes: date) -> str:
    """'5-11 oct' o, si cruza de mes, '28 sep-4 oct'."""
    fin = lunes + timedelta(days=6)
    if lunes.month == fin.month:
        return f"{lunes.day}-{fin.day} {MESES[fin.month - 1]}"
    return f"{lunes.day} {MESES[lunes.month - 1]}-{fin.day} {MESES[fin.month - 1]}"


def etiqueta_semana(lunes: date) -> str:
    """'S41 · 5-11 oct'."""
    return f"S{numero_semana(lunes)} · {rango_semana(lunes)}"


def semanas_disponibles(registradas, hoy: date | None = None, extra: int = 8) -> list[date]:
    """Semanas que se pueden modificar: las que tienen datos más las últimas
    `extra` semanas de calendario (para poder cargar una que se olvidó).
    Ordenadas de la más reciente a la más antigua."""
    actual = lunes_de(hoy or date.today())
    recientes = {actual - timedelta(weeks=k) for k in range(extra + 1)}
    return sorted(set(registradas) | recientes, reverse=True)


def matriz_historico(datos: dict, semanas: list[date], catalogo: dict):
    """Arma lo que muestra el histórico.

    Devuelve (encabezados, filas, totales):
      - encabezados: un texto por semana, con su total de horas
      - filas: [código, nombre, horas de cada semana..., total de la fila]
      - totales: horas de cada semana (solo iniciativas del catálogo)
    """
    totales = [sum(datos.get((s, c), 0) for c in catalogo) for s in semanas]
    encabezados = [f"{etiqueta_semana(s)} · {t:g} h" for s, t in zip(semanas, totales)]
    filas = []
    for codigo, nombre in catalogo.items():
        horas = [datos.get((s, codigo)) for s in semanas]
        suma = sum(h for h in horas if h is not None)
        filas.append([codigo, nombre, *map(fmt_horas, horas), fmt_horas(suma)])
    return encabezados, filas, totales
