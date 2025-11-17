# thumbnail_generator.py
from PIL import Image
from pathlib import Path
import os
import hashlib # Movido arriba
import cv2 # <-- IMPORTACIÓN NUEVA

THUMBNAIL_SIZE = (128, 128)
THUMBNAIL_DIR = Path(".visagevault_cache/thumbnails")

def get_thumbnail_path(original_filepath: str) -> Path:
    """Genera la ruta donde se guardará la miniatura."""
    file_hash = hashlib.sha256(original_filepath.encode('utf-8')).hexdigest()
    return THUMBNAIL_DIR / f"{file_hash}.jpg"

# --- RENOMBRADA: de 'generate_thumbnail' a 'generate_image_thumbnail' ---
def generate_image_thumbnail(original_filepath: str) -> str | None:
    """
    Genera una miniatura para una IMAGEN y la guarda en caché.
    Devuelve la ruta de la miniatura o None si falla.
    """
    original_filepath = Path(original_filepath)
    if not original_filepath.is_file():
        return None

    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    thumbnail_path = get_thumbnail_path(str(original_filepath))

    if thumbnail_path.exists():
        return str(thumbnail_path)

    try:
        with Image.open(original_filepath) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            img.save(thumbnail_path, "JPEG")
        return str(thumbnail_path)
    except Exception as e:
        print(f"❌ Error crítico generando miniatura de IMAGEN para {original_filepath}: {e}")
        return None

def generate_video_thumbnail(original_filepath: str) -> str | None:
    """
    Genera una miniatura para un VÍDEO usando OpenCV y la guarda en caché.
    Devuelve la ruta de la miniatura o None si falla.
    """
    original_filepath = Path(original_filepath)
    if not original_filepath.is_file():
        return None

    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    thumbnail_path = get_thumbnail_path(str(original_filepath))

    if thumbnail_path.exists():
        return str(thumbnail_path)

    try:
        # Abrir el vídeo
        cap = cv2.VideoCapture(str(original_filepath))

        # Intentar leer el primer frame
        success, frame = cap.read()
        cap.release()

        if not success:
            raise Exception("No se pudo leer el primer frame del vídeo.")

        # El 'frame' es un array de numpy (H, W, C)
        # Redimensionar manteniendo el aspecto
        h, w = frame.shape[:2]
        if h > w:
            new_h = THUMBNAIL_SIZE[1]
            new_w = int(w * (new_h / h))
        else:
            new_w = THUMBNAIL_SIZE[0]
            new_h = int(h * (new_w / w))

        resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Guardar la imagen
        cv2.imwrite(str(thumbnail_path), resized_frame)

        return str(thumbnail_path)

    except Exception as e:
        print(f"❌ Error crítico generando miniatura de VÍDEO para {original_filepath}: {e}")
        return None

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


    thumb_path = generate_image_thumbnail(img_test_path)
    if thumb_path:
        print(f"Miniatura generada/encontrada en: {thumb_path}")
    clear_thumbnail_cache()
    if Path(img_test_path).exists():
        os.remove(img_test_path) # Limpiar archivo de prueba
