# photo_finder.py
from pathlib import Path
import time

# --- CONFIGURACIÓN DE EXTENSIONES A BUSCAR ---
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tiff', '.webp')

def find_photos(directory_path: str) -> list[str]:
    """
    Busca archivos de imagen en un directorio dado (recursivamente).
    Devuelve las rutas como una lista de strings.
    """
    target_dir = Path(directory_path)
    if not target_dir.is_dir():
        # Si la ruta no existe o no es un directorio, devolvemos lista vacía
        return []

    photo_files = []

    count = 0
    # **.rglob('*')** busca recursivamente todos los archivos
    for file_path in target_dir.rglob('*'):
        # Comprobamos si es un archivo y si su extensión es compatible
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            # Convertimos Path a string para fácil manejo
            photo_files.append(str(file_path))

        # --- SIMULACIÓN DE TRABAJO PESADO ---
        # Esto asegura que podemos probar la fluidez del threading
        count += 1
        if count % 100 == 0:
             time.sleep(0.001)
        # ------------------------------------

    return photo_files

if __name__ == "__main__":
    # Ejemplo de prueba rápida (si tienes una carpeta de imágenes)
    test_dir = Path.home() / "Imágenes"
    print(f"Buscando en: {test_dir}")
    if test_dir.is_dir():
        results = find_photos(str(test_dir))
        print(f"Encontradas {len(results)} fotos.")
    else:
        print("No se encontró el directorio de prueba.")
