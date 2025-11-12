# thumbnail_generator.py
from PIL import Image
from pathlib import Path
import os

THUMBNAIL_SIZE = (128, 128)  # Tamaño estándar para miniaturas
THUMBNAIL_DIR = Path(".visagevault_cache/thumbnails") # Directorio para guardar miniaturas

def get_thumbnail_path(original_filepath: str) -> Path:
    """Genera la ruta donde se guardará la miniatura."""
    # Usamos un hash del filepath para el nombre del archivo de miniatura
    # Esto evita problemas con nombres de archivo largos o caracteres especiales
    import hashlib
    file_hash = hashlib.sha256(original_filepath.encode('utf-8')).hexdigest()
    return THUMBNAIL_DIR / f"{file_hash}.jpg"

def generate_thumbnail(original_filepath: str) -> str | None:
    """
    Genera una miniatura para la imagen dada y la guarda en caché.
    Devuelve la ruta de la miniatura o None si falla.
    """
    original_filepath = Path(original_filepath)
    if not original_filepath.is_file():
        return None

    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    thumbnail_path = get_thumbnail_path(str(original_filepath))

    if thumbnail_path.exists():
        return str(thumbnail_path) # Ya existe, la devolvemos

    try:
        with Image.open(original_filepath) as img:
            # Asegúrate de que el archivo es legible antes de intentar procesar
            img.thumbnail(THUMBNAIL_SIZE)
            img.save(thumbnail_path, "JPEG")
        return str(thumbnail_path)
    except Exception as e:
        # ⬅️ IMPORTANTE: Imprime el error para ver por qué falla
        print(f"❌ Error crítico generando miniatura para {original_filepath}: {e}")
        return None # Devuelve None si falla

# Para limpiar el caché de miniaturas (útil para desarrollo)
def clear_thumbnail_cache():
    """Elimina todos los archivos de miniaturas guardados."""
    if THUMBNAIL_DIR.exists():
        for item in THUMBNAIL_DIR.iterdir():
            if item.is_file():
                os.remove(item)
        THUMBNAIL_DIR.rmdir()
        print("Caché de miniaturas limpiado.")

if __name__ == '__main__':
    # Ejemplo de uso
    # Asegúrate de tener una imagen 'test.jpg' en el mismo directorio
    # y luego ejecuta este archivo: python thumbnail_generator.py

    # Crear un archivo dummy para probar si no tienes uno
    from PIL import Image, ImageDraw
    img_test_path = "test_image.jpg"
    if not Path(img_test_path).exists():
        test_img = Image.new('RGB', (60, 30), color = 'red')
        d = ImageDraw.Draw(test_img)
        d.text((10,10), "Test", fill=(255,255,0))
        test_img.save(img_test_path)
        print(f"Creado archivo de prueba: {img_test_path}")


    thumb_path = generate_thumbnail(img_test_path)
    if thumb_path:
        print(f"Miniatura generada/encontrada en: {thumb_path}")
    clear_thumbnail_cache()
    if Path(img_test_path).exists():
        os.remove(img_test_path) # Limpiar archivo de prueba
