# ==============================================================================
# PROYECTO: VisageVault - Gestor de Fotografías Inteligente
# VERSIÓN: 0.1 pre-release
# DERECHOS DE AUTOR: © 2025 Daniel Serrano Armenta
# ==============================================================================
#
# Autor: Daniel Serrano Armenta
# Contacto: dani.eus79@gmail.com
# GitHub: github.com/danitxu79
# Portafolio: https://danitxu79.github.io/
#
# --- LICENCIA Y DERECHOS DE USO ---
#
# Este software está disponible bajo un doble modelo de licencia:
#
# 1. USO NO COMERCIAL (Licencia Pública):
#    El código base está licenciado bajo la **GNU Lesser General Public License v3 (LGPLv3)**.
#    Esto permite el uso, estudio, modificación y distribución para fines personales,
#    educativos y no comerciales. Las modificaciones al código principal deben
#    mantenerse abiertas bajo LGPLv3.
#
# 2. USO COMERCIAL (Licencia Propietaria):
#    Para cualquier uso comercial, lucrativo o que requiera evitar las restricciones
#    de copyleft de la LGPLv3, es OBLIGATORIO adquirir una **Licencia Comercial
#    Propietaria**.
#
#    Para adquirir una licencia comercial, por favor contacte al autor en:
#    dani.eus79@gmail.com
#
# ==============================================================================

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QDialogButtonBox
)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QStyle, QFileDialog,
    QScrollArea, QGridLayout, QLabel, QGroupBox, QSpacerItem, QSizePolicy,
    QSplitter
)
from PySide6.QtCore import (
    Qt, QSize, QObject, Signal, QThread, Slot, QTimer,
    QRunnable, QThreadPool
)
from PySide6.QtGui import QPixmap, QIcon

# --- Importamos módulos auxiliares (ASUMIDOS EXISTENTES) ---
from photo_finder import find_photos
import config_manager
from metadata_reader import get_photo_date
from thumbnail_generator import generate_thumbnail, THUMBNAIL_SIZE
import metadata_reader
import piexif.helper
import re
import db_manager
from db_manager import VisageVaultDB

# Constante para el margen de precarga (en píxeles)
PRELOAD_MARGIN_PX = 500

# =================================================================
# DEFINICIÓN ÚNICA DE SEÑALES PARA EL THUMBNAILLOADER
# =================================================================
class ThumbnailLoaderSignals(QObject):
    """Contenedor de señales para la clase QRunnable."""
    thumbnail_loaded = Signal(str, QPixmap) # original_path, pixmap
    load_failed = Signal(str)

# =================================================================
# CLASE PARA CARGAR MINIATURAS EN UN HILO SEPARADO (QRunnable)
# =================================================================
class ThumbnailLoader(QRunnable):
    """QRunnable para cargar una miniatura de forma asíncrona."""

    def __init__(self, original_filepath: str, signals: ThumbnailLoaderSignals):
        super().__init__()
        self.original_filepath = original_filepath
        # Recibimos las señales como un argumento
        self.signals = signals

    @Slot()
    def run(self):
        # ... (La lógica de run() es la misma, usando self.signals) ...
        thumbnail_path = generate_thumbnail(self.original_filepath)
        if thumbnail_path:
            try:
                pixmap = QPixmap(thumbnail_path)
                self.signals.thumbnail_loaded.emit(self.original_filepath, pixmap)
            except Exception:
                self.signals.load_failed.emit(self.original_filepath)
        else:
            self.signals.load_failed.emit(self.original_filepath)

# -----------------------------------------------------------------
# NUEVA CLASE: ZoomableClickableLabel (Combina Zoom y Doble Clic)
# -----------------------------------------------------------------
class ZoomableClickableLabel(QLabel):
    """
    Un QLabel que emite una señal de doble clic y maneja el zoom
    con la rueda del ratón.
    """
    # Señal para el doble clic (para la vista de miniaturas)
    doubleClickedPath = Signal(str)

    def __init__(self, original_path=None, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.setAlignment(Qt.AlignCenter)

        # Atributos para el Zoom
        self._original_pixmap = QPixmap()
        self._current_scale = 1.0
        self.setMinimumSize(1, 1) # Importante para el zoom

    def setOriginalPixmap(self, pixmap: QPixmap):
        """Establece la imagen base (alta resolución) para el zoom."""
        self._original_pixmap = pixmap
        self.fitToWindow() # Ajuste inicial

    def fitToWindow(self):
        """Ajusta la imagen al tamaño actual del label (resetea el zoom)."""
        if self._original_pixmap.isNull():
            return
        self._current_scale = 1.0
        self.setPixmap(self._original_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))

    def wheelEvent(self, event):
        """Maneja el evento de la rueda del ratón para el zoom."""
        if self._original_pixmap.isNull():
            return # No hacer zoom si no hay imagen

        angle = event.angleDelta().y()
        if angle > 0:
            self._current_scale *= 1.15 # Zoom In
        else:
            self._current_scale /= 1.15 # Zoom Out

        # Limitar el zoom para que no sea demasiado pequeño
        if self._original_pixmap.size().width() * self._current_scale < 10:
             self._current_scale = 10 / self._original_pixmap.size().width()

        self._updateScaledPixmap()

    def _updateScaledPixmap(self):
        """Aplica el zoom actual al pixmap original."""
        if self._original_pixmap.isNull():
            return

        new_size = self._original_pixmap.size() * self._current_scale
        self.setPixmap(self._original_pixmap.scaled(
            new_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))

    def mouseDoubleClickEvent(self, event):
        """Maneja el doble clic (para la vista de miniaturas)."""
        if self.original_path:
            self.doubleClickedPath.emit(self.original_path)
        super().mouseDoubleClickEvent(event)

# -----------------------------------------------------------------
# CLASE MODIFICADA: PhotoDetailDialog (con Splitter y guardado de año)
# -----------------------------------------------------------------
class PhotoDetailDialog(QDialog):
    """
    Ventana de detalle con splitter vertical, zoom y edición de metadatos.
    """
    # Señal para notificar a la ventana principal que los datos cambiaron
    metadata_changed = Signal(str, str, str) # (photo_path, old_year, new_year)

    def __init__(self, original_path, db_manager: VisageVaultDB, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.db = db_manager  # ⬅️ Debes guardar la referencia a la BD
        self.exif_dict = {}
        # Guardará la info de la etiqueta de fecha: (ifd_name, tag_id, row_index)
        self.date_time_tag_info = None

        self.setWindowTitle(Path(original_path).name)
        self.resize(1000, 800)

        self._setup_ui()
        self._load_photo()
        self._load_metadata()

    def _setup_ui(self):
        # 1. Layout Principal (Vertical)
        layout = QVBoxLayout(self)

        # 2. SPLITTER VERTICAL (Imagen / Metadatos)
        self.splitter = QSplitter(Qt.Vertical)

        # 3. Área de la Imagen (Usando el nuevo Label)
        self.image_label = ZoomableClickableLabel() # Sin 'original_path'
        self.splitter.addWidget(self.image_label)

        # 4. Contenedor para Metadatos y Botones
        metadata_container = QWidget()
        metadata_layout = QVBoxLayout(metadata_container)

        year_edit_layout = QHBoxLayout()
        year_label = QLabel("Año (Edición rápida):")
        self.year_edit = QLineEdit()
        self.year_edit.setMaximumWidth(80) # Ancho fijo para 4 dígitos

        year_edit_layout.addWidget(year_label)
        year_edit_layout.addWidget(self.year_edit)
        year_edit_layout.addStretch() # Empuja los widgets a la izquierda

        # Añadimos el layout del año ANTES de la tabla
        metadata_layout.addLayout(year_edit_layout)

        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(2)
        self.metadata_table.setHorizontalHeaderLabels(["Metadato", "Valor"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metadata_table.setSelectionMode(QAbstractItemView.SingleSelection)
        metadata_layout.addWidget(self.metadata_table)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        button_box.accepted.connect(self._save_metadata)
        button_box.rejected.connect(self.reject)
        metadata_layout.addWidget(button_box)

        self.splitter.addWidget(metadata_container) # Añadir contenedor al splitter

        # 5. Ajustar tamaños iniciales del splitter (70% foto, 30% metadatos)
        self.splitter.setSizes([700, 300])

        # 6. Añadir splitter al layout principal
        layout.addWidget(self.splitter)

    def _load_photo(self):
        """Carga la foto completa y la pasa al label de zoom."""
        try:
            pixmap = QPixmap(self.original_path)
            self.image_label.setOriginalPixmap(pixmap)
        except Exception as e:
            self.image_label.setText(f"Error al cargar imagen: {e}")

    def _load_metadata(self):
        """Lee los EXIF y los carga en la tabla."""
        self.exif_dict = metadata_reader.get_exif_dict(self.original_path)
        self.metadata_table.setRowCount(0)
        self.date_time_tag_info = None # Resetear

        if not self.exif_dict:
            # ... (código para "No se encontraron metadatos") ...
            self.year_edit.setPlaceholderText("N/A")
            self.year_edit.setEnabled(True)

        row = 0
        found_year = False # ⬅️ AÑADIR ESTA BANDERA
        for ifd_name, tags in self.exif_dict.items():
            if not isinstance(tags, dict): continue

            for tag_id, value in tags.items():
                self.metadata_table.insertRow(row)
                tag_name = piexif.TAGS[ifd_name].get(tag_id, {"name": f"UnknownTag_{tag_id}"})["name"]

                # ... (decodificación de value_str como antes) ...
                if isinstance(value, bytes):
                    try: value_str = piexif.helper.decode_bytes(value)
                    except: value_str = str(value)
                else:
                    value_str = str(value)

                # --- !! LÓGICA MODIFICADA !! ---
                if tag_name in ['DateTimeOriginal', 'DateTime'] and not found_year:
                    self.date_time_tag_info = (ifd_name, tag_id, row)

                    # Extraer el año (YYYY) de "YYYY:MM:DD..."
                    current_year = self.db.get_photo_year(self.original_path)

                    if current_year:
                        self.year_edit.setText(current_year)
                    else:
                        # Si por alguna razón no está en la BD (raro), lo calculamos
                        year_from_meta = metadata_reader.get_photo_date(self.original_path)
                        self.year_edit.setText(year_from_meta)

    def _save_metadata(self):
        """
        Guarda el año modificado EN LA BASE DE DATOS.
        (Ya no modifica el EXIF, solo la BD)
        """
        try:
            # 1. Obtener el AÑO NUEVO del QLineEdit
            new_year_str = self.year_edit.text()

            # 2. Validar (simple)
            if not (new_year_str == "Sin Fecha" or (len(new_year_str) == 4 and new_year_str.isdigit())):
                print(f"Error: El Año debe ser 'Sin Fecha' o un número de 4 dígitos.")
                return

            # 3. Obtener el AÑO ANTIGUO (desde la BD)
            old_year = self.db.get_photo_year(self.original_path)

            # 4. Guardar el AÑO NUEVO en la BD
            self.db.update_photo_year(self.original_path, new_year_str)

            # 5. Emitir señal si el año cambió
            if old_year != new_year_str:
                self.metadata_changed.emit(self.original_path, old_year, new_year_str)

            self.accept()

        except Exception as e:
            print(f"Error al guardar el año en la BD: {e}")

    def resizeEvent(self, event):
        """Se llama cuando la ventana cambia de tamaño, para re-ajustar la foto."""
        # Solo reajustamos si el zoom está en el nivel base
        if self.image_label._current_scale == 1.0:
            self.image_label.fitToWindow()
        super().resizeEvent(event)

# =================================================================
# CLASE TRABAJADORA DEL ESCANEO (QObject, Corre en QThread)
# =================================================================
class PhotoFinderWorker(QObject):
    """
    Clase que ejecuta el escaneo de archivos y la lectura de metadatos.
    """
    finished = Signal(dict) # Emite las fotos agrupadas por año: { '2023': [path1, ...], ... }
    progress = Signal(str)   # Emite mensajes de estado

    def __init__(self, directory_path: str, db_manager: VisageVaultDB):
        super().__init__()
        self.directory_path = directory_path
        self.db = db_manager

    @Slot()
    def run(self):
        # Inicializa variables en un ámbito seguro
        photo_paths_on_disk = []
        """
        Lógica de escaneo MODIFICADA. Ahora usa la BD como fuente de verdad.
        """
        self.progress.emit("Cargando años conocidos desde la BD...")

        # 1. Cargar todos los años conocidos desde la BD
        db_years = self.db.load_all_photo_years()

        try:
            self.progress.emit("Escaneando archivos en el directorio...")

            # 2. Escanear el disco
            photo_paths_on_disk = find_photos(self.directory_path)

            photos_by_year = {}
            photos_to_upsert_in_db = [] # Lista de (filepath, year)

            # 3. Comparar Disco vs BD
            for i, path in enumerate(photo_paths_on_disk):

                # 3a. La foto ya está en la BD (la BD manda)
                if path in db_years:
                    year = db_years[path]

                # 3b. Foto nueva (no está en la BD)
                else:
                    self.progress.emit(f"Procesando nueva foto: {Path(path).name}")
                    # Usamos metadata_reader solo para el año INICIAL
                    year = metadata_reader.get_photo_date(path)
                    # La añadimos a la lista para guardarla en la BD
                    photos_to_upsert_in_db.append((path, year))

                # 4. Agrupar para la GUI
                if year not in photos_by_year:
                    photos_by_year[year] = []
                photos_by_year[year].append(path)

            # 5. Guardar todas las fotos nuevas en la BD de una sola vez
            if photos_to_upsert_in_db:
                self.progress.emit(f"Guardando {len(photos_to_upsert_in_db)} fotos nuevas en la BD...")
                self.db.bulk_upsert_photos(photos_to_upsert_in_db)

        except Exception as e:
            self.progress.emit(f"Error crítico durante el escaneo: {e}")
            # Si hay un error, photo_paths_on_disk sigue siendo [].

        # ⬅️ Usa la variable correctamente inicializada
        self.progress.emit(f"Escaneo finalizado. Encontradas {len(photo_paths_on_disk)} fotos.")
        self.finished.emit(photos_by_year)

# =================================================================
# VENTANA PRINCIPAL DE LA APLICACIÓN (VisageVaultApp)
# =================================================================
class VisageVaultApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisageVault")
        self.setMinimumSize(QSize(900, 600))

        self.db = VisageVaultDB()

        self.current_directory = None
        self.photos_by_year = {}

        # Hilos para el escaneo principal
        self.thread = None
        self.worker = None

        # Pool de hilos para cargar miniaturas (mejor para muchas tareas pequeñas)
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(os.cpu_count() or 4)

        # NUEVO: Objeto de señales global para todos los ThumbnailLoaders
        self.thumb_signals = ThumbnailLoaderSignals()

        # Conectar las señales globales a los slots de la aplicación
        self.thumb_signals.thumbnail_loaded.connect(self._update_thumbnail)
        self.thumb_signals.load_failed.connect(self._handle_thumbnail_failed)

        self._setup_ui()

        # Iniciar la comprobación inicial después de que la ventana se muestre
        QTimer.singleShot(100, self._initial_check)


    def _setup_ui(self):
        # 1. El QSplitter AHORA es el Widget Central
        self.main_splitter = QSplitter(Qt.Horizontal)

        # --- IZQUIERDA: Área de Fotos (Scroll) ---
        # (Esta parte es casi igual, pero la añadimos al splitter)
        photo_area_widget = QWidget()
        self.photo_container_layout = QVBoxLayout(photo_area_widget)
        self.photo_container_layout.addStretch(1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(photo_area_widget)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._load_visible_thumbnails)

        # Añadimos el área de scroll al splitter
        self.main_splitter.addWidget(self.scroll_area)

        # --- DERECHA: Barra de Navegación (Panel) ---
        # (Necesitamos un QWidget contenedor para el panel derecho)
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)

        # A. Botón y Ruta
        top_controls = QVBoxLayout()
        self.select_dir_button = QPushButton("Cambiar Directorio")
        self.select_dir_button.clicked.connect(self._open_directory_dialog)
        top_controls.addWidget(self.select_dir_button)

        self.path_label = QLabel("Ruta: No configurada")
        self.path_label.setWordWrap(True)
        top_controls.addWidget(self.path_label)
        right_panel_layout.addLayout(top_controls) # Añadir a right_panel_layout

        # B. Lista de Años
        year_label = QLabel("Años Encontrados:")
        right_panel_layout.addWidget(year_label) # Añadir a right_panel_layout

        self.year_list_widget = QListWidget()
        # Quitamos el setMaximumWidth(110) para que el splitter lo controle
        self.year_list_widget.currentRowChanged.connect(self._scroll_to_year)
        right_panel_layout.addWidget(self.year_list_widget) # Añadir a right_panel_layout

        # C. Etiqueta de Estado
        self.status_label = QLabel("Estado: Inicializando...")
        right_panel_layout.addWidget(self.status_label) # Añadir a right_panel_layout

        # Añadimos el panel derecho (el QWidget) al splitter
        self.main_splitter.addWidget(right_panel_widget)

        # --- Ensamblar el layout principal ---
        # El QSplitter es ahora el widget central de la ventana
        self.setCentralWidget(self.main_splitter)
        self._set_status("Aplicación iniciada. Comprobando configuración...")

        right_panel_widget.setMinimumWidth(150)
        # --- Conectar y Cargar el Estado del Splitter ---
        self.main_splitter.splitterMoved.connect(self._save_splitter_state)
        self._load_splitter_state()

    # ----------------------------------------------------
    # Lógica de Inicio y Configuración
    # ----------------------------------------------------

    def _initial_check(self):
        """Comprueba la configuración al arrancar la app."""
        directory = config_manager.get_photo_directory()

        if directory and Path(directory).is_dir():
            self.current_directory = directory
            self.path_label.setText(f"Ruta: {Path(directory).name}")
            self._start_photo_search(directory)
        else:
            self._set_status("No se encontró un directorio válido. Por favor, selecciona uno.")
            self._open_directory_dialog(force_select=True)

    def _open_directory_dialog(self, force_select=False):
        """Abre el diálogo para seleccionar el directorio."""
        dialog_title = "Selecciona la Carpeta Raíz de Fotos"
        directory = QFileDialog.getExistingDirectory(self, dialog_title, os.path.expanduser("~"))

        if directory:
            self.current_directory = directory
            config_manager.set_photo_directory(directory)
            self.path_label.setText(f"Ruta: {Path(directory).name}")
            self.year_list_widget.clear()
            self._start_photo_search(directory)
        elif force_select:
             self._set_status("¡Debes seleccionar un directorio para comenzar!")

    # ----------------------------------------------------
    # Lógica de Hilos y Resultados
    # ----------------------------------------------------

    def _start_photo_search(self, directory):
        """Configura y lanza el trabajador de escaneo."""
        if self.thread and self.thread.isRunning():
            self._set_status("El escaneo anterior sigue en curso.")
            return

        self.thread = QThread()
        self.worker = PhotoFinderWorker(directory, self.db)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._handle_search_finished)
        self.worker.progress.connect(self._set_status)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._on_scan_thread_finished)

        self.select_dir_button.setEnabled(False)
        self.thread.start()

    @Slot(dict)
    def _handle_search_finished(self, photos_by_year):
        """Recibe las fotos agrupadas y actualiza la GUI."""
        self.photos_by_year = photos_by_year
        self.select_dir_button.setEnabled(True)

        num_fotos = sum(len(p) for p in photos_by_year.values())
        self._set_status(f"Escaneo y metadatos finalizados. {num_fotos} fotos encontradas.")

        self._display_photos()

    # ----------------------------------------------------
    # Lógica de Visualización y Miniaturas
    # ----------------------------------------------------

    def _display_photos(self):
        """Muestra las fotos agrupadas y llena la barra de años."""

        # 1. Limpiar el layout de fotos anterior
        while self.photo_container_layout.count() > 0:
            item = self.photo_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                pass # Evitar borrar el stretch item si aún no hay nada

        self.year_list_widget.clear()

        # 2. Ordenar por año (descendente)
        sorted_years = sorted(self.photos_by_year.keys(), reverse=True)

        self.year_group_widgets = {}

        for year in sorted_years:
            photos = self.photos_by_year[year]

            # --- Crear el Grupo por Año ---
            year_group = QGroupBox(f"Año {year} ({len(photos)} fotos)")
            year_group.setObjectName(f"year_group_{year}")
            # Layout de rejilla para las fotos dentro del grupo
            year_layout = QGridLayout(year_group)

            self.year_group_widgets[year] = year_group

            # --- Crear los placeholders de las fotos ---
            for i, photo_path in enumerate(photos):
                photo_label = ZoomableClickableLabel(photo_path)
                # Ajustamos el tamaño fijo basado en el tamaño de la miniatura
                photo_label.setFixedSize(THUMBNAIL_SIZE[0] + 10, THUMBNAIL_SIZE[1] + 25)
                photo_label.setToolTip(photo_path)
                photo_label.setAlignment(Qt.AlignCenter)
                photo_label.setText(Path(photo_path).name.split('.')[0] + "\nCargando...")

                # Almacenamos la ruta original para que el cargador la sepa
                photo_label.setProperty("original_path", photo_path)
                # NUEVO: Marcamos el estado inicial como NO_CARGADO
                photo_label.setProperty("loaded", False)

                photo_label.doubleClickedPath.connect(self._open_photo_detail)

                row = i // 5
                col = i % 5
                year_layout.addWidget(photo_label, row, col)

            # Asegurar que las fotos se empujan hacia la izquierda
            year_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding), year_layout.rowCount(), 0)

            self.photo_container_layout.addWidget(year_group)
            self.year_list_widget.addItem(year)

        self.photo_container_layout.addStretch(1) # Stretch al final del layout principal

        # Iniciar la carga de miniaturas para las visibles al inicio
        QTimer.singleShot(500, self._load_visible_thumbnails)


    def _load_visible_thumbnails(self):
        """Carga las miniaturas de las fotos visibles y un margen de precarga."""
        viewport = self.scroll_area.viewport()

        # 1. Crear el rectángulo de precarga (más grande que el viewport)
        # .adjusted(izquierda, arriba, derecha, abajo)
        # Añadimos margen arriba (negativo) y abajo (positivo)
        preload_rect = viewport.rect().adjusted(0, -PRELOAD_MARGIN_PX, 0, PRELOAD_MARGIN_PX)

        # 2. Iteramos sobre TODOS los widgets hijos del CONTENEDOR del scroll
        # (Usamos self.scroll_area.widget() para acceder al 'photo_area_widget' interno)
        for photo_label in self.scroll_area.widget().findChildren(QLabel):
            original_path = photo_label.property("original_path")
            is_loaded = photo_label.property("loaded")

            if original_path and is_loaded is False:

                # 3. Usamos tu corrección con mapTo para obtener la geometría correcta
                label_pos = photo_label.mapTo(viewport, photo_label.rect().topLeft())
                label_rect_in_viewport = photo_label.rect().translated(label_pos)

                # 4. Comprobar intersección con el RECTÁNGULO DE PRECARGA
                if preload_rect.intersects(label_rect_in_viewport):
                    # Marcamos como en proceso
                    photo_label.setProperty("loaded", None)
                    loader = ThumbnailLoader(original_path, self.thumb_signals)
                    self.threadpool.start(loader)


    @Slot(str, QPixmap)
    def _update_thumbnail(self, original_path: str, pixmap: QPixmap):
        """Actualiza el QLabel con la miniatura cargada (ejecutado en el hilo principal)."""

        for photo_label in self.scroll_area.viewport().findChildren(QLabel):
            if photo_label.property("original_path") == original_path:
                # Escalamos el pixmap y lo asignamos
                photo_label.setPixmap(pixmap.scaled(THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1], Qt.KeepAspectRatio, Qt.SmoothTransformation))
                photo_label.setText("") # Quitar texto "Cargando..."

                # NUEVO: Marcamos como CARGADA
                photo_label.setProperty("loaded", True)
                break

    @Slot(int)
    def _scroll_to_year(self, row):
        """Mueve la barra de desplazamiento al grupo de año seleccionado."""
        if row >= 0:
            year = self.year_list_widget.item(row).text()
            target_group = self.year_group_widgets.get(year)

            if target_group:
                # Asegura que el widget sea visible en el área de scroll
                self.scroll_area.ensureWidgetVisible(target_group, 50, 50)

                # Cargar las miniaturas del área visible tras el scroll
                QTimer.singleShot(200, self._load_visible_thumbnails)

    def _set_status(self, message):
        self.status_label.setText(f"Estado: {message}")

    @Slot(str)
    def _handle_thumbnail_failed(self, original_path: str):
        """Maneja el caso en que la miniatura no se pudo cargar."""
        for photo_label in self.scroll_area.viewport().findChildren(QLabel):
            if photo_label.property("original_path") == original_path:
                photo_label.setText("Error al cargar.")
                photo_label.setProperty("loaded", True) # Marcar como "terminado" para no reintentar
                break

    @Slot()
    def _save_splitter_state(self):
        """Guarda las posiciones del splitter en la configuración."""
        sizes = self.main_splitter.sizes()
        config_data = config_manager.load_config()
        config_data['splitter_sizes'] = sizes
        config_manager.save_config(config_data)

    def _load_splitter_state(self):
        """Carga las posiciones del splitter desde la configuración."""
        config_data = config_manager.load_config()
        sizes = config_data.get('splitter_sizes')

        # Definir el ancho mínimo (DEBE SER EL MISMO que en _setup_ui)
        min_right_width = 150

        if sizes and len(sizes) == 2:
            # Asegurarse de que el tamaño cargado respeta el mínimo
            if sizes[1] < min_right_width:
                # Ajusta el tamaño izquierdo para compensar
                sizes[0] = sizes[0] + (sizes[1] - min_right_width)
                # Forza el tamaño mínimo derecho
                sizes[1] = min_right_width

            self.main_splitter.setSizes(sizes)
        else:
            # Si no hay configuración, establecemos un 80% / 20% por defecto
            default_width = self.width()
            default_sizes = [int(default_width * 0.8), int(default_width * 0.2)]

            # Asegurarse de que el valor por defecto respeta el mínimo
            if default_sizes[1] < min_right_width:
                 default_sizes[1] = min_right_width
                 default_sizes[0] = default_width - min_right_width

            self.main_splitter.setSizes(default_sizes)

    @Slot()
    def _on_scan_thread_finished(self):
        """
        Slot de limpieza que se llama cuando el QThread ha terminado.
        Resetea las variables de Python.
        """
        self.thread = None
        self.worker = None

    @Slot(str)
    def _open_photo_detail(self, original_path):
        """Abre la ventana de detalle de la foto."""
        self._set_status(f"Abriendo detalle para: {Path(original_path).name}")

        # Creamos y ejecutamos el diálogo
        # 'self' es el 'parent' para que el diálogo se centre sobre la app
        dialog = PhotoDetailDialog(original_path, self.db, self)
        dialog.metadata_changed.connect(self._handle_photo_year_changed)
        dialog.exec() # .exec() la hace modal (bloquea la ventana principal)

        self._set_status("Detalle cerrado.")

    @Slot()
    def _trigger_full_rescan(self):
        """
        Limpia la GUI y vuelve a escanear el directorio.
        Se llama cuando un metadato (como el año) ha cambiado.
        """
        self._set_status("Metadatos cambiados. Re-escaneando el directorio...")

        # Limpiar la GUI
        self.year_list_widget.clear()
        while self.photo_container_layout.count() > 0:
            item = self.photo_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Volver a escanear (esto reconstruirá los grupos de años)
        if self.current_directory:
            self._start_photo_search(self.current_directory)

    @Slot(str, str, str)
    def _handle_photo_year_changed(self, photo_path: str, old_year: str, new_year: str):
        """
        Actualiza el modelo de datos en memoria y reconstruye la GUI
        sin re-escanear el disco.
        """
        self._set_status(f"Moviendo foto de {old_year} a {new_year}...")

        # 1. Actualizar el modelo de datos (self.photos_by_year)

        # Quitar la foto de la lista del año antiguo
        if old_year in self.photos_by_year and photo_path in self.photos_by_year[old_year]:
            self.photos_by_year[old_year].remove(photo_path)
            # Si la lista del año antiguo queda vacía, eliminamos la clave
            if not self.photos_by_year[old_year]:
                del self.photos_by_year[old_year]

        # Añadir la foto a la lista del año nuevo
        if new_year not in self.photos_by_year:
            self.photos_by_year[new_year] = [] # Crear el nuevo año si no existe

        self.photos_by_year[new_year].append(photo_path)

        # 2. Reconstruir la GUI
        # Llamamos a _display_photos(), que limpia y reconstruye la vista
        # usando el diccionario self.photos_by_year actualizado.
        self._display_photos()

        self._set_status(f"Foto movida a {new_year}.")

        # 3. (Opcional) Resaltar el nuevo año en la lista
        items = self.year_list_widget.findItems(new_year, Qt.MatchExactly)
        if items:
            self.year_list_widget.setCurrentItem(items[0])


def run_visagevault():
    """Función para iniciar la aplicación gráfica."""
    app = QApplication(sys.argv)
    window = VisageVaultApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_visagevault()
