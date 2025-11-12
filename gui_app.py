import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog,
    QListWidget, QStyle
)
from PySide6.QtCore import Qt, QSize, QObject, Signal, QThread, Slot
from visagevault import find_photos # ⬅️ Importamos la lógica de búsqueda

# =================================================================
# CLASE TRABAJADORA (WORKER)
# Ejecuta la tarea pesada en un hilo separado
# =================================================================
class PhotoFinderWorker(QObject):
    """
    Clase QObject que ejecutará la función find_photos.
    Debe heredar de QObject para poder usar señales.
    """
    # Señales para comunicar resultados y progreso al hilo principal
    finished = Signal(list)  # Emite la lista final de fotos (lista de strings)
    progress = Signal(str)   # Emite mensajes de estado

    def __init__(self, directory_path):
        super().__init__()
        self.directory_path = directory_path

    @Slot()
    def run(self):
        """Método que se ejecuta cuando el QThread comienza."""
        self.progress.emit(f"Iniciando escaneo recursivo en: {self.directory_path}")

        # 1. Ejecutar la función pesada
        photos = find_photos(self.directory_path)

        # 2. Emitir el resultado
        self.finished.emit(photos)


# =================================================================
# VENTANA PRINCIPAL DE LA APLICACIÓN
# =================================================================
class PhotoManagerApp(QMainWindow):
    """Ventana principal de la aplicación de gestión de fotos."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Fotos Avanzado (PySide6)")
        self.setMinimumSize(QSize(800, 600))

        self.current_directory = ""
        self.current_photos = []

        # Variables para manejar el hilo y el trabajador
        self.thread = None
        self.worker = None

        self._setup_ui()
        self._set_status("Listo para buscar fotos.")

    def _setup_ui(self):
        # ... [La estructura de la UI es la misma] ...
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Layout Superior para Búsqueda (Horizontal)
        search_layout = QHBoxLayout()

        self.path_input = QLineEdit("Seleccione un directorio...")
        self.path_input.setReadOnly(True)
        self.path_input.setStyleSheet("background-color: #f0f0f0;")

        style = QApplication.style()
        folder_icon = style.standardIcon(QStyle.SP_DirHomeIcon)

        self.select_dir_button = QPushButton(folder_icon, "Seleccionar Directorio")
        # ⬅️ Conectamos el botón al nuevo método de inicio
        self.select_dir_button.clicked.connect(self._open_directory_dialog)

        search_layout.addWidget(self.path_input)
        search_layout.addWidget(self.select_dir_button)

        # Widget Central de Contenido (Lista de resultados)
        self.photo_list_widget = QListWidget()
        self.photo_list_widget.setStyleSheet("font-size: 10pt;")

        # Etiqueta para mensajes de estado
        self.status_label = QLabel("Estado: Listo.")

        # Ensamblar el Layout Principal
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.photo_list_widget)
        main_layout.addWidget(self.status_label) # Añadimos la barra de estado

        self.setCentralWidget(central_widget)

    def _set_status(self, message):
        """Actualiza la etiqueta de estado."""
        self.status_label.setText(f"Estado: {message}")

    def _open_directory_dialog(self):
        """Abre el diálogo y, si se selecciona, inicia la búsqueda en un nuevo hilo."""
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio de Fotos", os.path.expanduser("~"))

        if directory:
            self.current_directory = directory
            self.path_input.setText(directory)
            self.photo_list_widget.clear() # Limpiar resultados anteriores
            self._set_status("Directorio seleccionado. Iniciando búsqueda...")

            self._start_photo_search(directory)

    def _start_photo_search(self, directory):
        """
        Configura y lanza el trabajador en un QThread separado.
        """
        # 1. Crear el objeto QThread y el Worker (QObject)
        self.thread = QThread()
        self.worker = PhotoFinderWorker(directory)

        # 2. Mover el Worker al Thread
        # El Worker no debe heredar de QThread. Se MUEVE a él.
        self.worker.moveToThread(self.thread)

        # 3. Conectar señales del Worker a los Slots (métodos) de la GUI

        # Cuando el thread inicie, queremos que el worker ejecute su método 'run'
        self.thread.started.connect(self.worker.run)

        # Cuando el worker termine, queremos manejar los resultados
        self.worker.finished.connect(self._handle_search_finished)

        # Cuando el worker emita progreso, queremos actualizar el estado
        self.worker.progress.connect(self._handle_search_progress)

        # Cuando el worker termine, queremos también detener y limpiar el hilo
        self.worker.finished.connect(self.thread.quit)      # Detener el bucle de eventos del hilo
        self.worker.finished.connect(self.worker.deleteLater) # Eliminar el worker
        self.thread.finished.connect(self.thread.deleteLater) # Eliminar el thread

        # 4. Deshabilitar la interfaz para evitar múltiples búsquedas
        self.select_dir_button.setEnabled(False)

        # 5. ¡Lanzar el hilo!
        self.thread.start()

    @Slot(str)
    def _handle_search_progress(self, message):
        """Maneja los mensajes de progreso del worker."""
        self._set_status(message)

    @Slot(list)
    def _handle_search_finished(self, photo_paths):
        """
        Slot que recibe la lista de fotos del worker.
        Este método SIEMPRE se ejecuta en el hilo principal de la GUI.
        """
        self.current_photos = photo_paths

        # 1. Actualizar la lista de la GUI
        self.photo_list_widget.clear()
        if photo_paths:
            self.photo_list_widget.addItems(
                [f"{os.path.basename(p)} ({p})" for p in photo_paths[:20]]
                # Solo mostramos los primeros 20 para no sobrecargar
            )
        else:
            self.photo_list_widget.addItem("No se encontraron fotos compatibles.")

        # 2. Restaurar la interfaz
        self.select_dir_button.setEnabled(True)
        self._set_status(f"Búsqueda finalizada. Encontradas {len(photo_paths)} fotos.")


def run_gui():
    """Función para iniciar la aplicación gráfica."""
    app = QApplication(sys.argv)
    window = PhotoManagerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()
