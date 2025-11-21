# metadata_reader.py
import re
from datetime import datetime
from pathlib import Path

def get_photo_date(filepath: str) -> tuple[str, str]:
    """
    Determina la fecha de una foto de forma RÁPIDA (Sin leer EXIF).
    Prioridad:
    1. Patrón en el nombre del archivo (ej: IMG-20250402-...).
    2. Fecha de modificación del archivo (sistema de archivos).
    Devuelve una tupla (año, mes).
    """
    filename = Path(filepath).name

    # 1. Buscar patrón en el nombre del archivo (Muy rápido)
    match = re.search(r'IMG-(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            # '20250402' -> datetime object
            dt = datetime.strptime(date_str, '%Y%m%d')
            return str(dt.year), f"{dt.month:02d}"
        except ValueError:
            pass

    # 2. Usar fecha de modificación del archivo (stat)
    try:
        stat = Path(filepath).stat()
        dt_mod = datetime.fromtimestamp(stat.st_mtime)
        return str(dt_mod.year), f"{dt_mod.month:02d}"
    except Exception:
        return "Sin Fecha", "00"

def get_video_date(filepath: str) -> tuple[str, str]:
    """
    Determina la fecha de un vídeo usando la fecha de modificación.
    """
    try:
        stat = Path(filepath).stat()
        dt_mod = datetime.fromtimestamp(stat.st_mtime)
        return str(dt_mod.year), f"{dt_mod.month:02d}"
    except Exception:
        return "Sin Fecha", "00"
