# db_manager.py

import sqlite3
from pathlib import Path

class VisageVaultDB:
    """
    Clase que maneja la conexión y las operaciones de la base de datos SQLite.
    Cada método abre y cierra su propia conexión para ser seguro en múltiples hilos.
    """
    def __init__(self, db_file="visagevault.db"):
        self.db_file = db_file
        # No almacenamos self.connection aquí para evitar errores de multihilo
        self.create_tables()

    def _get_connection(self):
        """Función auxiliar para obtener una conexión local al hilo."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self):
        """Define y crea las tablas si no existen."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 1. Tabla PHOTOS (MODIFICADA: Añadida la columna 'year')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT NOT NULL UNIQUE,
                    file_hash TEXT UNIQUE,
                    year TEXT
                )
            """)

            # 2. Tabla FACES (Datos de reconocimiento)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY,
                    photo_id INTEGER NOT NULL,
                    encoding BLOB NOT NULL,
                    location TEXT,

                    FOREIGN KEY (photo_id) REFERENCES photos (id)
                )
            """)

            # 3. Tabla PEOPLE (Etiquetas de personas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            # 4. Tabla de Unión para etiquetar las caras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_labels (
                    face_id INTEGER NOT NULL,
                    person_id INTEGER NOT NULL,
                    PRIMARY KEY (face_id, person_id),
                    FOREIGN KEY (face_id) REFERENCES faces (id),
                    FOREIGN KEY (person_id) REFERENCES people (id)
                )
            """)

            conn.commit()
            print("Tablas verificadas y listas.")
        except sqlite3.Error as e:
            print(f"Error al crear tablas: {e}")
        finally:
            conn.close()

    # --- Funciones de Lectura (Usadas por PhotoFinderWorker) ---

    def load_all_photo_years(self) -> dict:
        """
        Carga todas las rutas y años conocidos desde la BD a un diccionario.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT filepath, year FROM photos")
            # Devuelve: {'/ruta/foto1.jpg': '2025', '/ruta/foto2.jpg': '2024'}
            return {row['filepath']: row['year'] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            print(f"Error al cargar años de la BD: {e}")
            return {}
        finally:
            conn.close()

    def bulk_upsert_photos(self, photos_data: list[tuple[str, str]]):
        """
        Inserta o reemplaza (si la ruta ya existe) una lista de fotos nuevas
        con su año inicial. Usado por el Worker al encontrar nuevas fotos.
        (photos_data es una lista de tuplas: (filepath, year))
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # 'INSERT OR IGNORE' solo inserta si la clave primaria no existe.
            # Necesitas 'INSERT OR REPLACE' si quisieras que el año se actualice
            # si la foto ya existe, pero para fotos nuevas, 'INSERT' basta.
            # Usaremos INSERT OR REPLACE para ser seguros con el 'year' y 'filepath'.
            cursor.executemany("""
                INSERT OR REPLACE INTO photos (filepath, year)
                VALUES (?, ?)
            """, photos_data)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error en bulk_upsert_photos: {e}")
        finally:
            conn.close()

    # --- Funciones de Edición (Usadas por PhotoDetailDialog) ---

    def update_photo_year(self, filepath: str, new_year: str):
        """Actualiza el año de una foto específica."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE photos SET year = ? WHERE filepath = ?", (new_year, filepath))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error al actualizar el año: {e}")
        finally:
            conn.close()

    def get_photo_year(self, filepath: str) -> str | None:
        """Obtiene el año guardado para una sola foto."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT year FROM photos WHERE filepath = ?", (filepath,))
            result = cursor.fetchone()
            return result['year'] if result else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    # El método close() ya no es estrictamente necesario, pero lo mantenemos como placeholder
    # para futuras funcionalidades que requieran un cierre explícito.
    def close(self):
        pass

if __name__ == "__main__":
    # Ejemplo de uso:
    db = VisageVaultDB(db_file="test_visagevault.db")
    print("\nPrueba de carga:")
    print(db.load_all_photo_years())

    # Pruebas de inserción
    test_data = [
        ("/home/test/foto1.jpg", "2024"),
        ("/home/test/foto2.jpg", "2025"),
    ]
    db.bulk_upsert_photos(test_data)
    print(db.load_all_photo_years())

    # Prueba de actualización
    db.update_photo_year("/home/test/foto1.jpg", "2023")
    print(db.get_photo_year("/home/test/foto1.jpg"))
    db.close()
