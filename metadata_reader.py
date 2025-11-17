# metadata_reader.py
import piexif
import re
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from pathlib import Path
from datetime import datetime
from pathlib import Path

def get_photo_date(filepath: str) -> tuple[str, str]:
    """
    Determina la fecha de una foto con la siguiente prioridad:
    1. Patrón en el nombre del archivo (ej: IMG-20250402-...).
    2. Metadatos EXIF ('DateTimeOriginal' o 'DateTime').
    3. Fecha de modificación del archivo.
    Devuelve una tupla (año, mes) o ("Sin Fecha", "00").
    """
    filename = Path(filepath).name

    # 1. Buscar patrón en el nombre del archivo
    match = re.search(r'IMG-(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            # '20250402' -> datetime object
            dt = datetime.strptime(date_str, '%Y%m%d')
            return str(dt.year), f"{dt.month:02d}"
        except ValueError:
            # El patrón existe pero la fecha no es válida, pasamos al siguiente método
            pass

    # 2. Si no hay patrón en el nombre, leer metadatos EXIF
    try:
        img = Image.open(filepath)
        exif_data = img.getexif()

        if exif_data:
            for tag_id, value in exif_data.items():
                if TAGS.get(tag_id) in ['DateTimeOriginal', 'DateTime']:
                    try:
                        dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        return str(dt.year), f"{dt.month:02d}"
                    except (ValueError, TypeError):
                        pass

        # 3. Si no hay EXIF, usar fecha de modificación
        stat = Path(filepath).stat()
        dt_mod = datetime.fromtimestamp(stat.st_mtime)
        return str(dt_mod.year), f"{dt_mod.month:02d}"

    except Exception:
        return "Sin Fecha", "00"

def get_exif_dict(filepath: str) -> dict:
    """
    Lee todos los metadatos EXIF de una imagen usando piexif.
    Devuelve un diccionario (puede estar vacío).
    """
    try:
        exif_dict = piexif.load(filepath)
        return exif_dict
    except Exception:
        # Si no hay EXIF o el formato no es compatible (ej. PNG)
        return {}

def save_exif_dict(filepath: str, exif_dict: dict):
    """
    Guarda el diccionario de metadatos EXIF en el archivo de imagen.
    """
    try:
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, filepath)
        print(f"Metadatos guardados en: {filepath}")
    except Exception as e:
        print(f"Error al guardar metadatos en {filepath}: {e}")

def get_video_date(filepath: str) -> tuple[str, str]:
    """
    Determina la fecha de un vídeo.
    Por ahora, solo usa la fecha de modificación del archivo.
    Devuelve una tupla (año, mes) o ("Sin Fecha", "00").
    """
    try:
        # Usar fecha de modificación del archivo
        stat = Path(filepath).stat()
        dt_mod = datetime.fromtimestamp(stat.st_mtime)
        return str(dt_mod.year), f"{dt_mod.month:02d}"
    except Exception:
        return "Sin Fecha", "00"
