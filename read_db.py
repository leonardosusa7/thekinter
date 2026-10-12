
import sqlite3
import sys
from pathlib import Path

# Ruta de la base de datos
DB_PATH = Path(
    sys.argv[1] if len(sys.argv) > 1 else "registro_horas.db"
)


def leer_base_datos():
    if not DB_PATH.exists():
        print(f"Error: No existe la base de datos: {DB_PATH.resolve()}")
        return

    try:
        # Abrir en modo de solo lectura
        conexion = sqlite3.connect(
            f"{DB_PATH.resolve().as_uri()}?mode=ro",
            uri=True
        )
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()

        # Obtener tablas
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        tablas = [fila["name"] for fila in cursor.fetchall()]

        print(f"\nBase de datos: {DB_PATH.resolve()}")
        print(f"Total de tablas: {len(tablas)}")

        if not tablas:
            print("No hay tablas.")
            return

        for tabla in tablas:
            # Escapar el nombre de tabla
            tabla_sql = '"' + tabla.replace('"', '""') + '"'

            cursor.execute(f"SELECT COUNT(*) FROM {tabla_sql}")
            total = cursor.fetchone()[0]

            print(f"\n{'=' * 60}")
            print(f"Tabla: {tabla} | Registros: {total}")
            print("=" * 60)

            # Mostrar estructura
            cursor.execute(f"PRAGMA table_info({tabla_sql})")
            columnas = [fila["name"] for fila in cursor.fetchall()]
            print("Columnas:", ", ".join(columnas))

            # Mostrar máximo 20 registros
            cursor.execute(f"SELECT * FROM {tabla_sql} LIMIT 45")
            registros = cursor.fetchall()

            for numero, registro in enumerate(registros, start=1):
                print(f"\nRegistro {numero}:")
                for columna in columnas:
                    print(f"  {columna}: {registro[columna]}")

            if total > 45:
                print(f"\n... Se muestran 20 de {total} registros.")

        conexion.close()

    except sqlite3.Error as error:
        print(f"Error SQLite: {error}")


if __name__ == "__main__":
    leer_base_datos()
