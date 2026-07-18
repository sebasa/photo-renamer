# Photo Renamer

Herramienta con interfaz gráfica para renombrar fotos de forma masiva usando un formato unificado de fecha y hora: `YYYY-MM-DD HH-MM-SS`.

Pensada para casos donde tenés fotos separadas por carpetas y querés unificar los nombres tomando la fecha de EXIF, fecha de modificación del archivo, o asignándola manualmente. Todo con un paso de análisis previo que muestra el resultado antes de aplicar ningún cambio.

## Características

- **Análisis previo no destructivo**: ves cómo va a quedar cada archivo antes de renombrar nada.
- **Fuentes de fecha configurables**:
  - EXIF (metadatos de la foto).
  - Fecha de modificación del archivo.
  - EXIF con fallback automático a fecha de modificación.
- **Override por archivo**: podés cambiar la fuente para filas específicas después del análisis.
- **Fecha manual**: asignar una fecha/hora arbitraria a los archivos seleccionados.
  - Si dejás la hora en blanco (solo `YYYY-MM-DD`), se conserva la hora original de cada archivo.
- **Copiar fecha de otro archivo**: seleccionás filas destino y copiás la fecha planificada de otro archivo de la misma carpeta.
- **Mantener nombre actual**: marca archivos seleccionados para excluirlos del renombrado.
- **Manejo de colisiones**: si dos archivos quedarían con el mismo nombre, agrega sufijos `_1`, `_2`, etc.
- **Modo recursivo**: procesa subcarpetas.
- **Log de operaciones**: genera un CSV con cada operación realizada para poder revertir manualmente si hace falta.
- **Interfaz con scroll**: tabla con scrollbar vertical y horizontal, y soporte para rueda del mouse.

## Formatos soportados

`.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.heic`, `.webp`, `.cr2`, `.nef`, `.arw`, `.dng`

> Nota: la extracción de EXIF depende de Pillow. Para `.heic` puede requerir instalar `pillow-heif` (no incluido por defecto).

## Requisitos

- Python 3.10 o superior
- Pillow

## Instalación

1. Instalar Python desde [python.org](https://www.python.org/downloads/). En Windows, marcar la opción **"Add Python to PATH"** durante la instalación.
2. Instalar la dependencia:

```bash
pip install Pillow
```

3. Descargar `photo_renamer.py` y ejecutarlo:

```bash
python photo_renamer.py
```

## Uso

1. **Elegir carpeta**: apuntá a la carpeta que contiene las fotos. Opcionalmente activá "Incluir subcarpetas".
2. **Elegir fuente de fecha**: por defecto usa EXIF con fallback a fecha de modificación.
3. **Analizar**: muestra la tabla con el nombre actual, la fuente usada, la fecha detectada y el nombre nuevo propuesto. No se toca ningún archivo todavía.
4. **Ajustar filas específicas** (opcional):
   - Seleccioná filas en la tabla (Ctrl+click para varias, Shift+click para rangos).
   - Usá los botones de override para cambiar fuente, asignar fecha manual, copiar de otro archivo, o mantener el nombre actual.
5. **Aplicar renombrado**: pide confirmación y ejecuta los cambios. Deja un archivo CSV de log en la carpeta raíz.

### Modo fecha manual

En el diálogo de fecha manual podés escribir:

- `2024-03-15 14:30:00` → aplica fecha y hora completas.
- `2024-03-15` → aplica solo la fecha y conserva la hora original de cada archivo.

Esto es útil cuando sabés en qué día se sacaron las fotos pero querés preservar el orden temporal entre ellas.

### Log de operaciones

Cada vez que ejecutás "Aplicar renombrado", se genera un archivo `_rename_log_YYYYMMDD_HHMMSS.csv` en la carpeta raíz con tres columnas: `original`, `nuevo`, `resultado`. Se puede usar para revertir manualmente los cambios si es necesario.

## Empaquetar como ejecutable (opcional)

Si querés distribuir el programa sin necesidad de instalar Python en la máquina destino:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed photo_renamer.py
```

El ejecutable queda en `dist/photo_renamer.exe`.

## Limitaciones conocidas

- No procesa archivos de video (solo imágenes).
- HEIC requiere `pillow-heif` instalado por separado.
- No hay función automática de "revertir": hay que hacerlo manualmente usando el CSV de log.
- La barra de progreso durante el análisis no está implementada; en carpetas muy grandes puede parecer que se congela la interfaz.

## Roadmap

Ideas pendientes:

- Soporte para metadatos de video (mp4, mov) con `ffprobe` o `hachoir`.
- Vista previa con miniaturas.
- Botón de "Revertir" que lea el CSV de log.
- Configuración persistente por carpeta.
- Calendario gráfico para el modo manual.
- Barra de progreso durante el análisis.

## Licencia

MIT.
