"""Catálogo de iniciativas.

Cámbialo por tu lista real, o cárgalo desde un CSV / base de datos.
El orden del diccionario es el orden en que aparecen las filas en la tabla.
"""

INICIATIVAS = {
    "INI-001": "Migración de pipelines a BigQuery",
    "INI-002": "Agente RAG de gestión del conocimiento",
    "INI-003": "Modelo de datos capa de transformación",
    "INI-004": "Monitoreo de calidad de datos",
    "INI-005": "Optimización de costos en Databricks",
}

TOPE_DEFECTO = 40  # horas máximas por semana (editable en pantalla)
