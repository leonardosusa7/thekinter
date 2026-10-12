# Registro de horas

Aplicación de escritorio en Python (tkinter + ttkbootstrap) para registrar las horas dedicadas a cada iniciativa y ver en tiempo real cuánto falta para el tope.

## Qué hace

- Login con contraseñas hasheadas (PBKDF2).
- **Ingresar horas:** tabla con todas las iniciativas, las últimas 4 semanas registradas en la base de datos como referencia y una columna editable para la semana actual.
- **Ver histórico:** todas las semanas registradas, con totales por semana y por iniciativa (solo lectura).
- **Modificar semana:** elegir cualquier semana y corregir sus horas.
- Nada se graba hasta pulsar **Guardar** (o Ctrl+S); si se intenta salir con cambios pendientes, la app pregunta.
- Total de la semana en vivo, con tope configurable y alertas de color.
- Datos en SQLite (`registro_horas.db`), separados por usuario y por semana.

## Requisitos

- Python 3.10 o superior
- [uv](https://docs.astral.sh/uv/) (gestor de entornos y dependencias)

## Instalación

```bash
git clone <URL-DEL-REPO>
cd registro-horas
uv sync
```

`uv sync` crea el entorno `.venv` e instala las versiones exactas definidas en `uv.lock`.

## Ejecución

```bash
uv run python main.py
```

Usuarios de ejemplo (solo para desarrollo, reemplazar antes de usar en serio):

| Usuario  | Contraseña    |
|----------|---------------|
| admin    | 1234          |
| leonardo | clave_segura  |

### Datos de prueba

Para llenar la base con horas aleatorias para cada iniciativa (por defecto, 8 semanas anteriores a la actual; la semana actual queda vacía):

```bash
uv run python db.py --demo admin        # 8 semanas
uv run python db.py --demo admin 20     # 20 semanas
```

La base `registro_horas.db` queda fuera de git (está en `.gitignore`). Para empezar de cero, bórrala.

## Estructura del proyecto

```
registro-horas/
├── main.py             # punto de entrada: login y luego la app
├── login.py            # ventana de login y validación
├── shell.py            # ventana principal: menú lateral + lista MODULOS
├── base.py             # clase Modulo (contrato) y Contexto (usuario + datos)
├── mod_ingresar.py     # módulo: ingresar las horas de la semana actual
├── mod_historico.py    # módulo: ver el histórico
├── mod_modificar.py    # módulo: modificar una semana específica
├── editor_semana.py    # tabla editable que usan "ingresar" y "modificar"
├── db.py               # guarda y lee las horas (SQLite), sin interfaz
├── utils.py            # funciones puras: fechas de semana, formato, matriz
├── catalogo.py         # lista de iniciativas y tope de horas
├── pyproject.toml      # dependencias y metadatos
├── uv.lock             # versiones exactas (no editar a mano)
└── README.md
```

Estructura objetivo cuando haya más módulos:

```
├── core/               # shell, menú, registro de módulos, autenticación
├── modules/            # una pantalla por archivo
└── services/           # lógica y acceso a datos, sin código de interfaz
```

## Cómo agregar un módulo nuevo

1. Crear `mod_nombre.py` con una clase que herede de `Modulo` (en `base.py`).
2. Definir `nombre` y dibujar la pantalla en `construir()`. Usar `self.ctx.usuario` y `self.ctx.repo` para los datos.
3. Si la pantalla puede tener cambios sin guardar, implementar `puede_salir()`; el menú lo consulta antes de cambiar de módulo o cerrar.
4. Agregar la clase a la lista `MODULOS` de `shell.py`. No hay que tocar nada más.
5. Las consultas nuevas van en `db.py` y los cálculos sin interfaz en `utils.py`, para poder probarlos sin abrir ventanas.

## Desarrollo

Agregar una dependencia de la app:

```bash
uv add nombre-paquete
```

Agregar una herramienta solo de desarrollo:

```bash
uv add --dev ruff pytest
```

Revisar y formatear el código:

```bash
uv run ruff check .
uv run ruff format .
```

Correr las pruebas:

```bash
uv run pytest
```

## Flujo de trabajo con git

1. Crear una rama por cambio: `git switch -c feature/nombre-corto`
2. Hacer commits pequeños con mensajes claros (`agrega módulo de usuarios`).
3. Antes de subir: `ruff check`, `pytest` y probar la app a mano.
4. Si cambiaste dependencias, subir `pyproject.toml` y `uv.lock` juntos.
5. Actualizar este README si cambió cómo se instala, se ejecuta o la estructura.

## Pendientes

- [ ] Conectar el catálogo de iniciativas a una fuente real (CSV o base de datos).
- [ ] Exportar el registro de horas.
- [ ] Reorganizar en carpetas `core/`, `modules/` y `services/` (hoy los archivos están sueltos).
- [ ] Pruebas automáticas con pytest para `utils.py` y `db.py`.
- [ ] Mover usuarios a una base de datos.

## Historial de cambios

### 0.3.0
- Menú lateral con tres módulos: ingresar horas, ver histórico y modificar semana.
- Botón Guardar (Ctrl+S) con cambios pendientes y aviso al salir sin guardar.
- La tabla muestra las últimas 4 semanas que existan en la base de datos, no las de calendario.
- Datos de prueba aleatorios para todas las iniciativas.

### 0.2.0
- La tabla muestra todas las iniciativas con las últimas 4 semanas y permite escribir las horas de la semana actual en la celda.
- Las horas se guardan en SQLite por usuario y semana.

### 0.1.0
- Login, módulo de registro de horas y tabla con total en vivo.
