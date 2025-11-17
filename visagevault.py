# ==============================================================================
# PROYECTO: VisageVault - Gestor de Fotografías Inteligente
# VERSIÓN: 1.1 (con Pestaña de Vídeos)
# DERECHOS DE AUTOR: © 2025 Daniel Serrano Armenta
# ==============================================================================
#
# Autor: Daniel Serrano Armenta
# Contacto: dani.eus79@gmail.com
# GitHub: github.com/danitxu79
# Portafolio: https://danitxu79.github.io/
#
# ## 📜 Licencia
#
# Este proyecto se ofrece bajo un modelo de Doble Licencia (Dual License), brindando máxima flexibilidad:
#
# 1. Licencia Pública (LGPLv3)
#
# Este software está disponible bajo la GNU Lesser General Public License v3.0 (LGPLv3).
# Puedes usarlo libremente de acuerdo con los términos de la LGPLv3, lo cual es ideal para proyectos de código abierto. En resumen, esto significa que si usas esta biblioteca
# (especialmente si la modificas), debes cumplir con las obligaciones de la LGPLv3, como publicar el código fuente de tus modificaciones a esta biblioteca y permitir que los usuarios
# la reemplacen.
# Puedes encontrar el texto completo de la licencia en el archivo LICENSE de este repositorio.
#
# 2. Licencia Comercial (Privativa)
#
# Si los términos de la LGPLv3 no se ajustan a tus necesidades, ofrezco una licencia comercial alternativa.
# Necesitarás una licencia comercial si, por ejemplo:
#
#    Deseas incluir el código en un software propietario (código cerrado) sin tener que publicar tus modificaciones.
#    Necesitas enlazar estáticamente (static linking) la biblioteca con tu aplicación propietaria.
#    Prefieres no estar sujeto a las obligaciones y restricciones de la LGPLv3.
#
# La licencia comercial te otorga el derecho a usar el código en tus aplicaciones comerciales de código cerrado sin las restricciones de la LGPLv3, a cambio de una tarifa.
# Para adquirir una licencia comercial o para más información, por favor, pónte en contacto conmigo en:
#
# dani.eus79@gmail.com
#
#
# ==============================================================================

import sys
import os
from pathlib import Path
import datetime
import locale
import warnings


# --- Silenciar solo el aviso de pkg_resources ---
warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API",
    category=UserWarning,
)

import numpy as np
from sklearn.cluster import DBSCAN
import sklearn

from PySide6.QtWidgets import (
    QDialog, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
    QComboBox, QMenu
)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QStyle, QFileDialog,
    QScrollArea, QGridLayout, QLabel, QGroupBox, QSpacerItem, QSizePolicy,
    QSplitter, QTabWidget, QStackedWidget
)
from PySide6.QtCore import (
    Qt, QSize, QObject, Signal, QThread, Slot, QTimer,
    QRunnable, QThreadPool, QPropertyAnimation, QEasingCurve, QRect, QPoint, QRectF,
    QPointF, QBuffer, QIODevice, QUrl
)
from PySide6.QtGui import (
    QPixmap, QIcon, QCursor, QTransform, QPainter, QPaintEvent,
    QPainterPath, QKeyEvent, QDesktopServices
)

# --- MODIFICADO: Importar las funciones de foto Y vídeo ---
from photo_finder import find_photos, find_videos
import config_manager
from metadata_reader import get_photo_date, get_video_date
from thumbnail_generator import (
    generate_image_thumbnail, generate_video_thumbnail, THUMBNAIL_SIZE
)
# --- FIN DE MODIFICACIÓN ---

import metadata_reader
import piexif.helper
import re
import db_manager
from db_manager import VisageVaultDB
import face_recognition
from PIL import Image
import ast
import pickle

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para dev y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Configuración regional para nombres de meses ---
try:
    locale.setlocale(locale.LC_TIME, '')
except locale.Error:
    print("Warning: Could not set system locale, month names may be in English.")


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
# CLASE PARA CARGAR MINIATURAS DE IMAGEN (QRunnable)
# =================================================================
class ThumbnailLoader(QRunnable):
    """QRunnable para cargar una miniatura de IMAGEN de forma asíncrona."""

    def __init__(self, original_filepath: str, signals: ThumbnailLoaderSignals):
        super().__init__()
        self.original_filepath = original_filepath
        self.signals = signals

    @Slot()
    def run(self):
        # --- MODIFICADO: Llama a la función específica de IMAGEN ---
        thumbnail_path = generate_image_thumbnail(self.original_filepath)
        # --- FIN DE MODIFICACIÓN ---
        if thumbnail_path:
            try:
                pixmap = QPixmap(thumbnail_path)
                self.signals.thumbnail_loaded.emit(self.original_filepath, pixmap)
            except Exception:
                self.signals.load_failed.emit(self.original_filepath)
        else:
            self.signals.load_failed.emit(self.original_filepath)

# =================================================================
# CLASE PARA CARGAR MINIATURAS DE VÍDEO (QRunnable) - ¡NUEVA!
# =================================================================
class VideoThumbnailLoader(QRunnable):
    """QRunnable para cargar una miniatura de VÍDEO de forma asíncrona."""

    def __init__(self, original_filepath: str, signals: ThumbnailLoaderSignals):
        super().__init__()
        self.original_filepath = original_filepath
        self.signals = signals

    @Slot()
    def run(self):
        # --- MODIFICADO: Llama a la función específica de VÍDEO ---
        thumbnail_path = generate_video_thumbnail(self.original_filepath)
        # --- FIN DE MODIFICACIÓN ---
        if thumbnail_path:
            try:
                pixmap = QPixmap(thumbnail_path)
                self.signals.thumbnail_loaded.emit(self.original_filepath, pixmap)
            except Exception:
                self.signals.load_failed.emit(self.original_filepath)
        else:
            self.signals.load_failed.emit(self.original_filepath)

# =================================================================
# SEÑALES Y WORKER PARA CARGAR Y RECORTAR CARAS (Sin cambios)
# =================================================================
class FaceLoaderSignals(QObject):
    face_loaded = Signal(int, QPixmap, str)
    face_load_failed = Signal(int)

class FaceLoader(QRunnable):
    def __init__(self, signals: FaceLoaderSignals, face_id: int, photo_path: str, location_str: str):
        super().__init__()
        self.signals = signals
        self.face_id = face_id
        self.photo_path = photo_path
        self.location_str = location_str

    @Slot()
    def run(self):
        try:
            location = ast.literal_eval(self.location_str)
            (top, right, bottom, left) = location
            img = Image.open(self.photo_path)
            face_image_pil = img.crop((left, top, right, bottom))

            pixmap = QPixmap()
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            face_image_pil.save(buffer, "PNG")
            pixmap.loadFromData(buffer.data())
            buffer.close()

            if pixmap.isNull():
                raise Exception("QPixmap nulo después de la conversión.")

            self.signals.face_loaded.emit(self.face_id, pixmap, self.photo_path)

        except Exception as e:
            print(f"Error en FaceLoader (ID: {self.face_id}): {e}")
            self.signals.face_load_failed.emit(self.face_id)

# =================================================================
# SEÑALES Y WORKER PARA AGRUPAR CARAS (CLUSTERING) (Sin cambios)
# =================================================================
class ClusterSignals(QObject):
    clusters_found = Signal(list)
    clustering_progress = Signal(str)
    clustering_finished = Signal()

class ClusterWorker(QRunnable):
    def __init__(self, signals: ClusterSignals, db_manager: VisageVaultDB):
        super().__init__()
        self.signals = signals
        self.db = db_manager

    @Slot()
    def run(self):
        try:
            self.signals.clustering_progress.emit("Cargando datos de caras...")
            face_data = self.db.get_unknown_face_encodings()

            if len(face_data) < 2:
                self.signals.clustering_progress.emit("No hay suficientes caras para comparar.")
                self.signals.clusters_found.emit([])
                self.signals.clustering_finished.emit()
                return

            self.signals.clustering_progress.emit(f"Comparando {len(face_data)} caras...")
            face_ids = [data[0] for data in face_data]
            encodings = np.array([data[1] for data in face_data])

            clt = DBSCAN(eps=0.4, min_samples=2, metric="euclidean")
            clt.fit(encodings)

            clusters = {}
            for face_id, label in zip(face_ids, clt.labels_):
                if label == -1:
                    continue
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(face_id)

            final_clusters_list = list(clusters.values())
            self.signals.clustering_progress.emit(f"Se encontraron {len(final_clusters_list)} grupos.")
            self.signals.clusters_found.emit(final_clusters_list)

        except Exception as e:
            print(f"Error crítico en el ClusterWorker: {e}")
            self.signals.clustering_progress.emit(f"Error: {e}")
        finally:
            self.signals.clustering_finished.emit()

# =================================================================
# CLASE PARA VISTA PREVIA CON ZOOM (QDialog) (Sin cambios)
# =================================================================
class ImagePreviewDialog(QDialog):
    is_showing = False
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        ImagePreviewDialog.is_showing = True
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._pixmap = pixmap
        self.label = ZoomableClickableLabel(self)
        self.label.is_thumbnail_view = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.animation = QPropertyAnimation(self, b"geometry")
    def show_with_animation(self):
        screen = QApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()
        img_size = self._pixmap.size()
        max_width = int(screen_geom.width() * 0.9)
        max_height = int(screen_geom.height() * 0.9)
        target_size = img_size
        if img_size.width() > max_width or img_size.height() > max_height:
            target_size = img_size.scaled(max_width, max_height, Qt.KeepAspectRatio)
        self.label.setOriginalPixmap(self._pixmap)
        self.resize(target_size)
        center_x = screen_geom.x() + (screen_geom.width() - target_size.width()) // 2
        center_y = screen_geom.y() + (screen_geom.height() - target_size.height()) // 2
        self.move(center_x, center_y)
        self.show()
    def close_with_animation(self):
        end_pos = QCursor.pos()
        end_geom = QRect(end_pos.x(), end_pos.y(), 1, 1)
        start_geom = self.geometry()
        self.animation.setDuration(200)
        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        self.animation.setEasingCurve(QEasingCurve.InQuad)
        self.animation.finished.connect(self._handle_close_animation_finished)
        self.animation.start()
    def _handle_close_animation_finished(self):
        ImagePreviewDialog.is_showing = False
        self.accept()
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.close_with_animation()
        else:
            super().keyPressEvent(event)
    def resizeEvent(self, event):
        if self.label._current_scale == 1.0:
            self.label.fitToWindow()
        super().resizeEvent(event)

# =================================================================
# CLASE PARA MOSTRAR CARAS RECORTADAS (Sin cambios)
# =================================================================
class CircularFaceLabel(QLabel):
    clicked = Signal()
    rightClicked = Signal(QPoint)
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Cara detectada (Haz clic para etiquetar)")
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = QPixmap()
        if pixmap and not pixmap.isNull():
            self.setPixmap(pixmap)
    def setPixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self._pixmap = QPixmap()
        else:
            self._pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.update()
    def paintEvent(self, event: QPaintEvent):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.end()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(event.globalPos())
        super().mousePressEvent(event)

# =================================================================
# CLASE: ZoomableClickableLabel (Sin cambios)
# =================================================================
class ZoomableClickableLabel(QLabel):
    doubleClickedPath = Signal(str)
    def __init__(self, original_path=None, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self._original_pixmap = QPixmap()
        self._current_scale = 1.0
        self._scale_factor = 1.15
        self._view_offset = QPointF(0.0, 0.0)
        self._panning = False
        self._last_mouse_pos = QPoint()
        self.is_thumbnail_view = False
        self.setCursor(Qt.OpenHandCursor)
    def setOriginalPixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self._original_pixmap = QPixmap()
        else:
            self._original_pixmap = pixmap
        self._current_scale = 1.0
        self._view_offset = QPointF(0.0, 0.0)
        self.fitToWindow()
    def fitToWindow(self):
        if self._original_pixmap.isNull():
            self.setPixmap(QPixmap())
            return
        scaled_pixmap = self._original_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        if self._original_pixmap.width() > 0:
            self._current_scale = scaled_pixmap.width() / self._original_pixmap.width()
        else:
            self._current_scale = 1.0
        self._clamp_view_offset()
        self.update()
    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if self.is_thumbnail_view:
                if event.angleDelta().y() < 0:
                    self._open_preview()
                else:
                    super().wheelEvent(event)
            else:
                if event.angleDelta().y() > 0:
                    parent_dialog = self.window()
                    if isinstance(parent_dialog, ImagePreviewDialog):
                        parent_dialog.close_with_animation()
            return
        if self.is_thumbnail_view:
            super().wheelEvent(event)
            return
        if self._original_pixmap.isNull():
            return
        old_scale = self._current_scale
        if event.angleDelta().y() > 0:
            self._current_scale *= self._scale_factor
        else:
            self._current_scale /= self._scale_factor
        mouse_pos_in_label = event.position()
        original_img_coords_before_zoom = QPointF(
            self._view_offset.x() + (mouse_pos_in_label.x() / old_scale),
            self._view_offset.y() + (mouse_pos_in_label.y() / old_scale)
        )
        self._view_offset = QPointF(
            original_img_coords_before_zoom.x() - (mouse_pos_in_label.x() / self._current_scale),
            original_img_coords_before_zoom.y() - (mouse_pos_in_label.y() / self._current_scale)
        )
        self._clamp_view_offset()
        self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_thumbnail_view:
            self._panning = True
            self._last_mouse_pos = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self._panning and not self.is_thumbnail_view:
            delta = event.position().toPoint() - self._last_mouse_pos
            self._view_offset -= QPointF(delta.x() / self._current_scale, delta.y() / self._current_scale)
            self._last_mouse_pos = event.position().toPoint()
            self._clamp_view_offset()
            self.update()
        else:
            super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_thumbnail_view:
            self._panning = False
            self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
    def mouseDoubleClickEvent(self, event):
        if self.is_thumbnail_view and self.original_path:
            self.doubleClickedPath.emit(self.original_path)
        if not self.is_thumbnail_view:
            self.fitToWindow()
        super().mouseDoubleClickEvent(event)
    def _clamp_view_offset(self):
        if self._original_pixmap.isNull() or self._current_scale == 0: return
        scaled_img_width = self._original_pixmap.width() * self._current_scale
        scaled_img_height = self._original_pixmap.height() * self._current_scale
        if scaled_img_width < self.width():
            self._view_offset.setX(0)
        else:
            max_x_offset = self._original_pixmap.width() - (self.width() / self._current_scale)
            self._view_offset.setX(max(0.0, min(self._view_offset.x(), max_x_offset)))
        if scaled_img_height < self.height():
            self._view_offset.setY(0)
        else:
            max_y_offset = self._original_pixmap.height() - (self.height() / self._current_scale)
            self._view_offset.setY(max(0.0, min(self._view_offset.y(), max_y_offset)))
    def paintEvent(self, event: QPaintEvent):
        if self.is_thumbnail_view:
            super().paintEvent(event)
            return
        if self._original_pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scaled_width = self._original_pixmap.width() * self._current_scale
        scaled_height = self._original_pixmap.height() * self._current_scale
        target_x = 0.0
        target_y = 0.0
        if scaled_width < self.width():
            target_x = (self.width() - scaled_width) / 2.0
        if scaled_height < self.height():
            target_y = (self.height() - scaled_height) / 2.0
        target_rect = QRectF(target_x, target_y, scaled_width, scaled_height)
        src_x = self._view_offset.x()
        src_y = self._view_offset.y()
        src_width = self.width() / self._current_scale
        src_height = self.height() / self._current_scale
        if scaled_width < self.width():
            src_width = self._original_pixmap.width()
        if scaled_height < self.height():
            src_height = self._original_pixmap.height()
        source_rect = QRectF(src_x, src_y, src_width, src_height)
        painter.drawPixmap(target_rect, self._original_pixmap, source_rect)
        painter.end()
    def resizeEvent(self, event):
        if not self.is_thumbnail_view:
            self.fitToWindow()
        super().resizeEvent(event)
    def _open_preview(self):
        if ImagePreviewDialog.is_showing:
            return
        if not self.original_path:
            return
        full_pixmap = QPixmap(self.original_path)
        if full_pixmap.isNull():
            return
        preview_dialog = ImagePreviewDialog(full_pixmap, self)
        preview_dialog.show_with_animation()

# -----------------------------------------------------------------
# CLASE MODIFICADA: PhotoDetailDialog (Sin cambios)
# -----------------------------------------------------------------
class PhotoDetailDialog(QDialog):
    metadata_changed = Signal(str, str, str)
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        self.image_label = ZoomableClickableLabel(self.original_path, self)
        self.image_label.is_thumbnail_view = False
        self.main_splitter.addWidget(self.image_label)
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_widget.setMinimumWidth(300)
        right_panel_widget.setMaximumWidth(450)
        date_group = QGroupBox("Fecha (Base de Datos)")
        date_layout = QGridLayout(date_group)
        date_layout.addWidget(QLabel("Año:"), 0, 0)
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("Ej: 2024 o 'Sin Fecha'")
        date_layout.addWidget(self.year_edit, 0, 1)
        date_layout.addWidget(QLabel("Mes:"), 1, 0)
        self.month_combo = QComboBox()
        self.month_combo.addItem("Mes Desconocido", "00")
        for i in range(1, 13):
            month_str = str(i).zfill(2)
            try:
                month_name = datetime.datetime.strptime(month_str, "%m").strftime("%B").capitalize()
            except ValueError:
                month_name = datetime.date(2000, i, 1).strftime("%B").capitalize()
            self.month_combo.addItem(month_name, month_str)
        date_layout.addWidget(self.month_combo, 1, 1)
        exif_group = QGroupBox("Datos EXIF (Solo Lectura)")
        exif_layout = QVBoxLayout(exif_group)
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(2)
        self.metadata_table.setHorizontalHeaderLabels(["Campo", "Valor"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.metadata_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.metadata_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        exif_layout.addWidget(self.metadata_table)
        right_panel_layout.addWidget(date_group)
        right_panel_layout.addWidget(exif_group, 1)
        self.main_splitter.addWidget(right_panel_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._save_metadata)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.main_splitter.setSizes([int(self.width() * 0.7), int(self.width() * 0.3)])
    def __init__(self, original_path, db_manager: VisageVaultDB, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.db = db_manager
        self.exif_dict = {}
        self.date_time_tag_info = None
        self.setWindowTitle(Path(original_path).name)
        self.resize(1000, 800)
        self._setup_ui()
        self._load_photo()
        self._load_metadata()
    def _load_photo(self):
        try:
            pixmap = QPixmap(self.original_path)
            self.image_label.setOriginalPixmap(pixmap)
        except Exception as e:
            self.image_label.setText(f"Error al cargar imagen: {e}")
    def _load_metadata(self):
        self.exif_dict = metadata_reader.get_exif_dict(self.original_path)
        self.metadata_table.setRowCount(0)
        current_year, current_month = self.db.get_photo_date(self.original_path)
        if current_year is None or current_month is None:
            exif_year, exif_month = metadata_reader.get_photo_date(self.original_path)
            if current_year is None:
                current_year = exif_year
            if current_month is None:
                current_month = exif_month
        self.year_edit.setText(current_year or "Sin Fecha")
        month_index = self.month_combo.findData(current_month or "00")
        self.month_combo.setCurrentIndex(month_index if month_index != -1 else 0)
        if not self.exif_dict:
            self.metadata_table.insertRow(0)
            self.metadata_table.setItem(0, 0, QTableWidgetItem("Info"))
            self.metadata_table.setItem(0, 1, QTableWidgetItem("No se encontraron metadatos EXIF."))
            return
        row = 0
        for ifd_name, tags in self.exif_dict.items():
            if not isinstance(tags, dict): continue
            for tag_id, value in tags.items():
                self.metadata_table.insertRow(row)
                tag_name = piexif.TAGS[ifd_name].get(tag_id, {"name": f"UnknownTag_{tag_id}"})["name"]
                if isinstance(value, bytes):
                    try: value_str = piexif.helper.decode_bytes(value)
                    except: value_str = str(value)
                else:
                    value_str = str(value)
                self.metadata_table.setItem(row, 0, QTableWidgetItem(tag_name))
                self.metadata_table.setItem(row, 1, QTableWidgetItem(value_str))
                row += 1
    def _save_metadata(self):
        try:
            new_year_str = self.year_edit.text()
            new_month_str = self.month_combo.currentData()
            if not (new_year_str == "Sin Fecha" or (len(new_year_str) == 4 and new_year_str.isdigit())):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self,
                                    "Datos Inválidos",
                                    "El Año debe ser 'Sin Fecha' o un número de 4 dígitos (ej: 2024).")
                return
            old_year, old_month = self.db.get_photo_date(self.original_path)
            if old_year != new_year_str or old_month != new_month_str:
                self.db.update_photo_date(self.original_path, new_year_str, new_month_str)
                self.metadata_changed.emit(self.original_path, new_year_str, new_month_str)
            self.accept()
        except Exception as e:
            print(f"Error al guardar la fecha en la BD: {e}")

# =================================================================
# CLASE: DIÁLOGO DE ETIQUETADO DE GRUPOS (CLUSTERS) (Sin cambios)
# =================================================================
class FaceClusterDialog(QDialog):
    SkipRole = QDialog.Accepted + 1
    DeleteRole = QDialog.Accepted + 2
    def __init__(self, db: VisageVaultDB, threadpool: QThreadPool,
                 face_ids: list, parent=None):
        super().__init__(parent)
        self.db = db
        self.threadpool = threadpool
        self.face_ids = face_ids
        self.local_face_signals = FaceLoaderSignals()
        self.local_face_signals.face_loaded.connect(self._on_dialog_face_loaded)
        self.setWindowTitle(f"Agrupar {len(self.face_ids)} Caras")
        self.setMinimumSize(600, 400)
        self.person_id_to_save = None
        self._setup_ui()
        self._load_people_combo()
        self._load_faces_async()
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        face_scroll_area = QScrollArea()
        face_scroll_area.setWidgetResizable(True)
        face_widget = QWidget()
        self.face_grid_layout = QGridLayout(face_widget)
        self.face_grid_layout.setSpacing(10)
        face_scroll_area.setWidget(face_widget)
        main_layout.addWidget(face_scroll_area, 1)
        assign_group = QGroupBox("Asignar Persona")
        assign_layout = QGridLayout(assign_group)
        assign_layout.addWidget(QLabel("Persona Existente:"), 0, 0)
        self.people_combo = QComboBox()
        self.people_combo.currentIndexChanged.connect(self._on_combo_changed)
        assign_layout.addWidget(self.people_combo, 0, 1)
        assign_layout.addWidget(QLabel("O Nueva Persona:"), 1, 0)
        self.new_person_edit = QLineEdit()
        self.new_person_edit.setPlaceholderText("Ej: Ana García")
        self.new_person_edit.textChanged.connect(self._on_text_changed)
        assign_layout.addWidget(self.new_person_edit, 1, 1)
        main_layout.addWidget(assign_group)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.skip_button = self.button_box.addButton("Siguiente", QDialogButtonBox.ButtonRole.ActionRole)
        self.skip_button.clicked.connect(self._skip)
        self.delete_button = self.button_box.addButton("Eliminar caras", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.delete_button.clicked.connect(self._delete_and_reject)
        self.button_box.accepted.connect(self._save_and_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
    def _load_people_combo(self):
        self.people_combo.addItem("--- Seleccionar ---", -1)
        people = self.db.get_all_people()
        for person_row in people:
            person_id = person_row['id']
            person_name = person_row['name']
            self.people_combo.addItem(person_name, person_id)
    def _load_faces_async(self):
        num_cols = max(1, (self.width() - 50) // 110)
        for i, face_id in enumerate(self.face_ids):
            face_widget = CircularFaceLabel(QPixmap())
            face_widget.setText("...")
            face_widget.setProperty("face_id", face_id)
            face_widget.clicked.connect(self._show_face_preview)
            row, col = i // num_cols, i % num_cols
            self.face_grid_layout.addWidget(face_widget, row, col, Qt.AlignTop)
            face_info = self.db.get_face_info(face_id)
            if face_info:
                loader = FaceLoader(
                    self.local_face_signals,
                    face_id,
                    face_info['filepath'],
                    face_info['location']
                )
                self.threadpool.start(loader)
    @Slot()
    def _on_combo_changed(self):
        if self.people_combo.currentIndex() > 0:
            self.new_person_edit.clear()
    @Slot()
    def _on_text_changed(self, text):
        if text:
            self.people_combo.setCurrentIndex(0)
    @Slot()
    def _save_and_accept(self):
        try:
            new_name = self.new_person_edit.text().strip()
            selected_id = self.people_combo.currentData()
            if new_name:
                person_id = self.db.add_person(new_name)
                if person_id == -1:
                    existing = self.db.get_person_by_name(new_name)
                    person_id = existing['id']
                self.person_id_to_save = person_id
            elif selected_id != -1:
                self.person_id_to_save = selected_id
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Acción Requerida",
                                    "Por favor, selecciona una persona existente o escribe un nombre nuevo.")
                return
            if self.person_id_to_save:
                for face_id in self.face_ids:
                    self.db.restore_face(face_id)
                    self.db.link_face_to_person(face_id, self.person_id_to_save)
                self.accept()
        except Exception as e:
            print(f"Error al guardar el cluster: {e}")
    @Slot(int, QPixmap, str)
    def _on_dialog_face_loaded(self, face_id: int, pixmap: QPixmap, photo_path: str):
        for i in range(self.face_grid_layout.count()):
            widget = self.face_grid_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'property') and widget.property("face_id") == face_id:
                widget.setPixmap(pixmap)
                widget.setText("")
                widget.setProperty("photo_path", photo_path)
                break
    @Slot()
    def _show_face_preview(self):
        sender_widget = self.sender()
        if not sender_widget:
            return
        photo_path = sender_widget.property("photo_path")
        if not photo_path:
            print("Por favor, espera a que la cara termine de cargar.")
            return
        full_pixmap = QPixmap(photo_path)
        if full_pixmap.isNull():
            print(f"Error: No se pudo cargar la imagen completa de {photo_path}")
            return
        preview_dialog = ImagePreviewDialog(full_pixmap, self)
        preview_dialog.setModal(True)
        preview_dialog.show_with_animation()
    @Slot()
    def _skip(self):
        self.done(self.SkipRole)
    @Slot()
    def _delete_and_reject(self):
        if self.face_ids:
            for face_id in self.face_ids:
                self.db.soft_delete_face(face_id)
        self.done(self.DeleteRole)

# =================================================================
# CLASE TRABAJADORA DEL ESCANEO DE FOTOS
# =================================================================
class PhotoFinderWorker(QObject):
    finished = Signal(dict)
    progress = Signal(str)

    def __init__(self, directory_path: str, db_manager: VisageVaultDB):
        super().__init__()
        self.directory_path = directory_path
        self.db = db_manager
        self.is_running = True

    @Slot()
    def run(self):
        photos_by_year_month = {}
        try:
            self.progress.emit("Cargando fechas de fotos conocidas desde la BD...")
            db_dates = self.db.load_all_photo_dates()

            self.progress.emit("Escaneando archivos de FOTOS en el directorio...")
            photo_paths_on_disk = find_photos(self.directory_path)
            photo_paths_on_disk_set = set(photo_paths_on_disk)

            photos_to_upsert_in_db = []

            for path in photo_paths_on_disk:
                if not self.is_running:
                    break
                if path in db_dates:
                    year, month = db_dates[path]
                else:
                    self.progress.emit(f"Procesando nueva foto: {Path(path).name}")
                    year, month = get_photo_date(path)
                    photos_to_upsert_in_db.append((path, year, month))

                if year not in photos_by_year_month:
                    photos_by_year_month[year] = {}
                if month not in photos_by_year_month[year]:
                    photos_by_year_month[year][month] = []
                photos_by_year_month[year][month].append(path)

            self.progress.emit("Buscando fotos eliminadas...")
            db_paths_set = set(db_dates.keys())
            paths_to_delete = list(db_paths_set - photo_paths_on_disk_set)

            if paths_to_delete:
                self.progress.emit(f"Eliminando {len(paths_to_delete)} fotos de la BD...")
                # Asumiendo que has creado 'bulk_delete_photos' en db_manager.py
                self.db.bulk_delete_photos(paths_to_delete)

            if photos_to_upsert_in_db:
                self.progress.emit(f"Guardando {len(photos_to_upsert_in_db)} fotos nuevas en la BD...")
                self.db.bulk_upsert_photos(photos_to_upsert_in_db)

            self.progress.emit(f"Escaneo de fotos finalizado. Encontradas {len(photo_paths_on_disk)} fotos.")

        except Exception as e:
            print(f"Error crítico en el hilo PhotoFinderWorker: {e}")
            self.progress.emit(f"Error en escaneo de fotos: {e}")
        finally:
            self.finished.emit(photos_by_year_month)

# =================================================================
# CLASE TRABAJADORA DEL ESCANEO DE VÍDEOS - ¡NUEVA!
# =================================================================
class VideoFinderWorker(QObject):
    finished = Signal(dict)
    progress = Signal(str)

    def __init__(self, directory_path: str, db_manager: VisageVaultDB):
        super().__init__()
        self.directory_path = directory_path
        self.db = db_manager
        self.is_running = True

    @Slot()
    def run(self):
        videos_by_year_month = {}
        try:
            self.progress.emit("Cargando fechas de vídeos conocidas desde la BD...")
            # --- MODIFICADO ---
            db_dates = self.db.load_all_video_dates()

            self.progress.emit("Escaneando archivos de VÍDEOS en el directorio...")
            video_paths_on_disk = find_videos(self.directory_path)
            video_paths_on_disk_set = set(video_paths_on_disk)

            videos_to_upsert_in_db = []

            for path in video_paths_on_disk:
                if not self.is_running:
                    break
                if path in db_dates:
                    year, month = db_dates[path]
                else:
                    self.progress.emit(f"Procesando nuevo vídeo: {Path(path).name}")
                    year, month = get_video_date(path)
                    videos_to_upsert_in_db.append((path, year, month))

                if year not in videos_by_year_month:
                    videos_by_year_month[year] = {}
                if month not in videos_by_year_month[year]:
                    videos_by_year_month[year][month] = []
                videos_by_year_month[year][month].append(path)

            self.progress.emit("Buscando vídeos eliminados...")
            db_paths_set = set(db_dates.keys())
            paths_to_delete = list(db_paths_set - video_paths_on_disk_set)

            if paths_to_delete:
                self.progress.emit(f"Eliminando {len(paths_to_delete)} vídeos de la BD...")
                # Asumiendo que has creado 'bulk_delete_videos' en db_manager.py
                self.db.bulk_delete_videos(paths_to_delete)

            if videos_to_upsert_in_db:
                self.progress.emit(f"Guardando {len(videos_to_upsert_in_db)} vídeos nuevos en la BD...")
                self.db.bulk_upsert_videos(videos_to_upsert_in_db)

            self.progress.emit(f"Escaneo de vídeos finalizado. Encontrados {len(video_paths_on_disk)} vídeos.")
            # --- FIN DE MODIFICACIÓN ---

        except Exception as e:
            print(f"Error crítico en el hilo VideoFinderWorker: {e}")
            self.progress.emit(f"Error en escaneo de vídeos: {e}")
        finally:
            self.finished.emit(videos_by_year_month)

# =================================================================
# CLASE TRABAJADORA DEL ESCANEO DE CARAS (Sin cambios)
# =================================================================
class FaceScanSignals(QObject):
    scan_progress = Signal(str)
    scan_percentage = Signal(int)
    face_found = Signal(int, str, str)
    scan_finished = Signal()

class FaceScanWorker(QObject):
    def __init__(self, db_manager: VisageVaultDB):
        super().__init__()
        self.db = db_manager
        self.signals = FaceScanSignals()
        self.is_running = True
    @Slot()
    def run(self):
        try:
            self.signals.scan_progress.emit("Buscando fotos sin escanear...")
            unscanned_photos = self.db.get_unscanned_photos()
            total = len(unscanned_photos)
            if total == 0:
                self.signals.scan_progress.emit("No hay fotos nuevas que escanear.")
                self.signals.scan_percentage.emit(100)
                self.signals.scan_finished.emit()
                return
            self.signals.scan_progress.emit(f"Escaneando {total} fotos nuevas para caras...")
            for i, row in enumerate(unscanned_photos):
                if not self.is_running:
                    break
                photo_id = row['id']
                photo_path = row['filepath']
                self.signals.scan_progress.emit(f"Procesando ({i+1}/{total}): {Path(photo_path).name}")
                percentage = (i + 1) * 100 // total
                self.signals.scan_percentage.emit(percentage)
                try:
                    image = face_recognition.load_image_file(photo_path)
                    locations = face_recognition.face_locations(image)
                    if not locations:
                        self.db.mark_photo_as_scanned(photo_id)
                        continue
                    encodings = face_recognition.face_encodings(image, locations)
                    for loc, enc in zip(locations, encodings):
                        location_str = str(loc)
                        encoding_blob = pickle.dumps(enc)
                        face_id = self.db.add_face(photo_id, encoding_blob, location_str)
                        self.signals.face_found.emit(face_id, photo_path, location_str)
                    self.db.mark_photo_as_scanned(photo_id)
                except Exception as e:
                    print(f"Error procesando caras en {photo_path}: {e}")
                    self.db.mark_photo_as_scanned(photo_id)
            self.signals.scan_progress.emit("Escaneo de caras finalizado.")
            self.signals.scan_finished.emit()
        except Exception as e:
            print(f"Error crítico en el hilo de escaneo de caras: {e}")
            self.signals.scan_progress.emit(f"Error: {e}")
            self.signals.scan_finished.emit()

# =================================================================
# VENTANA PRINCIPAL DE LA APLICACIÓN (VisageVaultApp)
# =================================================================
class VisageVaultApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisageVault")
        icon_path = resource_path("visagevault.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Advertencia: No se pudo encontrar el icono en {icon_path}")
        self.setMinimumSize(QSize(900, 600))
        self.db = VisageVaultDB()
        self.current_directory = None

        # --- Variables de Fotos ---
        self.photos_by_year_month = {}
        self.photo_thread = None
        self.photo_worker = None

        # --- Variables de Vídeos (NUEVO) ---
        self.videos_by_year_month = {}
        self.video_thread = None
        self.video_worker = None

        # --- Variables de Caras ---
        self.face_scan_thread = None
        self.face_scan_worker = None
        self.face_loading_label = None
        self.current_face_count = 0

        # --- Hilos y Señales ---
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(os.cpu_count() or 4)

        # Usamos la MISMA señal para todas las miniaturas (fotos, vídeos, caras)
        self.thumb_signals = ThumbnailLoaderSignals()
        self.thumb_signals.thumbnail_loaded.connect(self._update_thumbnail)
        self.thumb_signals.load_failed.connect(self._handle_thumbnail_failed)

        self.face_loader_signals = FaceLoaderSignals()
        self.face_loader_signals.face_loaded.connect(self._handle_face_loaded)
        self.face_loader_signals.face_load_failed.connect(self._handle_face_load_failed)

        self.cluster_queue = []
        self.cluster_signals = ClusterSignals()
        self.cluster_signals.clusters_found.connect(self._handle_clusters_found)
        self.cluster_signals.clustering_progress.connect(self._set_status)
        self.cluster_signals.clustering_finished.connect(self._handle_clustering_finished)

        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(200)
        self.resize_timer.timeout.connect(self._handle_resize_timeout)

        self._setup_ui()
        QTimer.singleShot(100, self._initial_check)


    def _setup_ui(self):
        # 1. Crear el QTabWidget
        self.tab_widget = QTabWidget()

        # ==========================================================
        # 2. Pestaña "Fotos"
        # ==========================================================
        fotos_tab_widget = QWidget()
        fotos_layout = QVBoxLayout(fotos_tab_widget)
        fotos_layout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QSplitter(Qt.Horizontal)

        # Panel Izquierdo (Fotos)
        photo_area_widget = QWidget()
        self.photo_container_layout = QVBoxLayout(photo_area_widget)
        self.photo_container_layout.setSpacing(20)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(photo_area_widget)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._load_main_visible_thumbnails)
        self.main_splitter.addWidget(self.scroll_area)

        # Panel Derecho (Navegación de Fotos)
        photo_right_panel_widget = QWidget()
        photo_right_panel_layout = QVBoxLayout(photo_right_panel_widget)

        # Controles superiores (Botón y Path)
        top_controls = QVBoxLayout()
        self.select_dir_button = QPushButton("Cambiar Directorio")
        self.select_dir_button.clicked.connect(self._open_directory_dialog)
        top_controls.addWidget(self.select_dir_button)
        self.path_label = QLabel("Ruta: No configurada")
        self.path_label.setWordWrap(True)
        top_controls.addWidget(self.path_label)
        photo_right_panel_layout.addLayout(top_controls)

        photo_year_label = QLabel("Navegación por Fecha (Fotos):")
        photo_right_panel_layout.addWidget(photo_year_label)
        self.date_tree_widget = QTreeWidget()
        self.date_tree_widget.setHeaderHidden(True)
        self.date_tree_widget.currentItemChanged.connect(self._scroll_to_item)
        photo_right_panel_layout.addWidget(self.date_tree_widget)

        self.status_label = QLabel("Estado: Inicializando...")
        photo_right_panel_layout.addWidget(self.status_label)
        self.main_splitter.addWidget(photo_right_panel_widget)

        fotos_layout.addWidget(self.main_splitter)

        # ==========================================================
        # 3. Pestaña "Vídeos" - ¡NUEVA!
        # (Copia de la pestaña de fotos, con nombres cambiados)
        # ==========================================================
        videos_tab_widget = QWidget()
        videos_layout = QVBoxLayout(videos_tab_widget)
        videos_layout.setContentsMargins(0, 0, 0, 0)

        self.video_splitter = QSplitter(Qt.Horizontal)

        # Panel Izquierdo (Vídeos)
        video_area_widget = QWidget()
        self.video_container_layout = QVBoxLayout(video_area_widget)
        self.video_container_layout.setSpacing(20)
        self.video_scroll_area = QScrollArea()
        self.video_scroll_area.setWidgetResizable(True)
        self.video_scroll_area.setWidget(video_area_widget)
        self.video_scroll_area.verticalScrollBar().valueChanged.connect(self._load_visible_video_thumbnails)
        self.video_splitter.addWidget(self.video_scroll_area)

        # Panel Derecho (Navegación de Vídeos)
        video_right_panel_widget = QWidget()
        video_right_panel_layout = QVBoxLayout(video_right_panel_widget)

        # (No necesitamos el botón de cambiar directorio aquí, solo el árbol)
        video_year_label = QLabel("Navegación por Fecha (Vídeos):")
        video_right_panel_layout.addWidget(video_year_label)
        self.video_date_tree_widget = QTreeWidget()
        self.video_date_tree_widget.setHeaderHidden(True)
        self.video_date_tree_widget.currentItemChanged.connect(self._scroll_to_video_item)
        video_right_panel_layout.addWidget(self.video_date_tree_widget)

        # Añadir un spacer para llenar
        video_right_panel_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.video_splitter.addWidget(video_right_panel_widget)

        videos_layout.addWidget(self.video_splitter)


        # ==========================================================
        # 4. Pestaña "Personas" (Sin cambios)
        # ==========================================================
        self.personas_tab_widget = QWidget()
        personas_layout = QVBoxLayout(self.personas_tab_widget)
        personas_layout.setContentsMargins(0, 0, 0, 0)
        self.people_splitter = QSplitter(Qt.Horizontal)
        self.left_people_stack = QStackedWidget()

        # Pagina 0: Cuadrícula de Caras
        face_area_widget = QWidget()
        self.face_container_layout = QVBoxLayout(face_area_widget)
        self.unknown_faces_group = QGroupBox("Caras Sin Asignar")
        self.unknown_faces_layout = QGridLayout(self.unknown_faces_group)
        self.unknown_faces_layout.setSpacing(10)
        self.face_container_layout.addWidget(self.unknown_faces_group)
        self.face_container_layout.addStretch(1)
        self.face_scroll_area = QScrollArea()
        self.face_scroll_area.setWidgetResizable(True)
        self.face_scroll_area.setWidget(face_area_widget)
        self.left_people_stack.addWidget(self.face_scroll_area)

        # Pagina 1: Cuadrícula de Fotos de Persona
        self.person_photo_scroll_area = QScrollArea()
        self.person_photo_scroll_area.setWidgetResizable(True)
        person_photo_widget = QWidget()
        self.person_photo_layout = QVBoxLayout(person_photo_widget)
        self.person_photo_scroll_area.setWidget(person_photo_widget)
        self.person_photo_scroll_area.verticalScrollBar().valueChanged.connect(self._load_person_visible_thumbnails)
        self.left_people_stack.addWidget(self.person_photo_scroll_area)
        self.people_splitter.addWidget(self.left_people_stack)

        # Panel Derecho (Personas)
        people_panel_widget = QWidget()
        people_panel_layout = QVBoxLayout(people_panel_widget)
        people_panel_widget.setMinimumWidth(180)
        people_panel_widget.setMaximumWidth(450)
        people_label = QLabel("Navegación por Personas:")
        people_panel_layout.addWidget(people_label)
        self.people_tree_widget = QTreeWidget()
        self.people_tree_widget.setHeaderHidden(True)
        self.people_tree_widget.currentItemChanged.connect(self._on_person_selected)
        people_panel_layout.addWidget(self.people_tree_widget)
        self.show_deleted_faces_button = QPushButton("Ver caras eliminadas")
        self.show_deleted_faces_button.clicked.connect(self._show_deleted_faces)
        people_panel_layout.addWidget(self.show_deleted_faces_button)
        self.cluster_faces_button = QPushButton("Buscar Duplicados")
        self.cluster_faces_button.clicked.connect(self._start_clustering)
        people_panel_layout.addWidget(self.cluster_faces_button)
        self.people_splitter.addWidget(people_panel_widget)
        personas_layout.addWidget(self.people_splitter)
        default_width = self.width()
        min_right_width = 180
        left_width = default_width - min_right_width
        if left_width < 100: left_width = 100
        self.people_splitter.setSizes([left_width, min_right_width])

        # ==========================================================
        # 5. Añadir pestañas al Widget Central
        # ==========================================================
        self.tab_widget.addTab(fotos_tab_widget, "Fotos")
        self.tab_widget.addTab(videos_tab_widget, "Vídeos") # <-- NUEVO
        self.tab_widget.addTab(self.personas_tab_widget, "Personas")
        self.setCentralWidget(self.tab_widget)

        # ==========================================================
        # 6. Cargar estado de los splitters
        # ==========================================================
        photo_right_panel_widget.setMinimumWidth(180)
        self.main_splitter.splitterMoved.connect(self._save_photo_splitter_state)
        self._load_photo_splitter_state()

        video_right_panel_widget.setMinimumWidth(180)
        self.video_splitter.splitterMoved.connect(self._save_video_splitter_state)
        self._load_video_splitter_state() # <-- NUEVO

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    # ----------------------------------------------------
    # Lógica de Inicio y Configuración
    # ----------------------------------------------------

    def _initial_check(self):
        """Comprueba la configuración al arrancar la app."""
        directory = config_manager.get_photo_directory()
        if directory and Path(directory).is_dir():
            self.current_directory = directory
            self.path_label.setText(f"Ruta: {Path(directory).name}")
            # --- MODIFICADO: Iniciar ambos escaneos ---
            self._start_media_scan(directory)
            # --- FIN DE MODIFICACIÓN ---
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
            self.date_tree_widget.clear()
            self.video_date_tree_widget.clear() # <-- NUEVO
            # --- MODIFICADO: Iniciar ambos escaneos ---
            self._start_media_scan(directory)
            # --- FIN DE MODIFICACIÓN ---
        elif force_select:
             self._set_status("¡Debes seleccionar un directorio para comenzar!")

    # ----------------------------------------------------
    # Lógica de Hilos y Resultados
    # ----------------------------------------------------

    def _start_media_scan(self, directory):
        """Inicia los escaneos de fotos y vídeos."""
        if not directory:
            return
        self._start_photo_search(directory)
        self._start_video_search(directory)

    def _start_photo_search(self, directory):
        """Configura y lanza el trabajador de escaneo de FOTOS."""
        if self.photo_thread and self.photo_thread.isRunning():
            self._set_status("El escaneo de fotos anterior sigue en curso.")
            return

        self.photo_thread = QThread()
        self.photo_worker = PhotoFinderWorker(directory, self.db)
        self.photo_worker.moveToThread(self.photo_thread)

        self.photo_thread.started.connect(self.photo_worker.run)
        self.photo_worker.finished.connect(self._handle_search_finished)
        self.photo_worker.progress.connect(self._set_status)

        self.photo_worker.finished.connect(self.photo_thread.quit)
        self.photo_worker.finished.connect(self.photo_worker.deleteLater)
        self.photo_thread.finished.connect(self._on_scan_thread_finished)

        self.select_dir_button.setEnabled(False)
        self.photo_thread.start()

    # --- NUEVA FUNCIÓN ---
    def _start_video_search(self, directory):
        """Configura y lanza el trabajador de escaneo de VÍDEOS."""
        if self.video_thread and self.video_thread.isRunning():
            self._set_status("El escaneo de vídeos anterior sigue en curso.")
            return

        self.video_thread = QThread()
        self.video_worker = VideoFinderWorker(directory, self.db)
        self.video_worker.moveToThread(self.video_thread)

        self.video_thread.started.connect(self.video_worker.run)
        self.video_worker.finished.connect(self._handle_video_search_finished)
        self.video_worker.progress.connect(self._set_status) # Ambos workers reportan al mismo status_label

        self.video_worker.finished.connect(self.video_thread.quit)
        self.video_worker.finished.connect(self.video_worker.deleteLater)
        self.video_thread.finished.connect(self._on_video_scan_thread_finished)

        self.select_dir_button.setEnabled(False) # Compartido
        self.video_thread.start()
    # --- FIN DE LO NUEVO ---

    # ----------------------------------------------------
    # Escaneo de caras (Sin cambios)
    # ----------------------------------------------------
    def _start_face_scan(self):
        """Configura y lanza el trabajador de escaneo de caras."""
        if self.face_scan_thread and self.face_scan_thread.isRunning():
            self._set_status("El escaneo de caras ya está en curso.")
            return
        self.face_scan_thread = QThread()
        self.face_scan_worker = FaceScanWorker(self.db)
        self.face_scan_worker.moveToThread(self.face_scan_thread)
        self.face_scan_worker.signals.scan_progress.connect(self._set_status)
        self.face_scan_worker.signals.scan_percentage.connect(self._update_face_scan_percentage)
        self.face_scan_worker.signals.face_found.connect(self._handle_face_found)
        self.face_scan_worker.signals.scan_finished.connect(self._handle_scan_finished)
        self.face_scan_thread.started.connect(self.face_scan_worker.run)
        self.face_scan_worker.signals.scan_finished.connect(self.face_scan_thread.quit)
        self.face_scan_worker.signals.scan_finished.connect(self.face_scan_worker.deleteLater)
        self.face_scan_thread.finished.connect(self._on_face_scan_thread_finished)
        self._set_status("Iniciando escaneo de caras...")
        self.face_scan_thread.start()

    # ----------------------------------------------------
    # Lógica de Visualización y Miniaturas
    # ----------------------------------------------------

    def _display_photos(self):
        """Muestra las FOTOS agrupadas por fecha."""
        while self.photo_container_layout.count() > 0:
            item = self.photo_container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.date_tree_widget.clear()

        self.photo_group_widgets = {} # Almacenará { 'year-month': widget }

        viewport_width = self.scroll_area.viewport().width() - 30
        thumb_width = THUMBNAIL_SIZE[0] + 10
        num_cols = max(1, viewport_width // thumb_width)

        sorted_years = sorted(self.photos_by_year_month.keys(), reverse=True)

        for year in sorted_years:
            if year == "Sin Fecha": continue
            year_item = QTreeWidgetItem(self.date_tree_widget, [str(year)])
            self.photo_group_widgets[year] = None

            sorted_months = sorted(self.photos_by_year_month[year].keys())

            year_group_box = QGroupBox(f"Año {year}")
            year_group_box.setObjectName(f"group_{year}")
            year_main_layout = QVBoxLayout(year_group_box)
            self.photo_group_widgets[year] = year_group_box

            for month in sorted_months:
                if month == "00": continue
                photos = self.photos_by_year_month[year][month]
                if not photos: continue

                try:
                    month_name = datetime.datetime.strptime(month, "%m").strftime("%B").capitalize()
                except ValueError:
                    month_name = "Mes Desconocido"

                month_item = QTreeWidgetItem(year_item, [f"{month_name} ({len(photos)})"])
                month_item.setData(0, Qt.UserRole, (year, month))

                month_label = QLabel(month_name)
                month_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 10px;")
                year_main_layout.addWidget(month_label)
                self.photo_group_widgets[f"{year}-{month}"] = month_label

                photo_grid_widget = QWidget()
                photo_grid_layout = QGridLayout(photo_grid_widget)
                photo_grid_layout.setSpacing(5)

                for i, photo_path in enumerate(photos):
                    photo_label = ZoomableClickableLabel(photo_path)
                    photo_label.is_thumbnail_view = True
                    photo_label.setFixedSize(THUMBNAIL_SIZE[0] + 10, THUMBNAIL_SIZE[1] + 25)
                    photo_label.setToolTip(photo_path)
                    photo_label.setAlignment(Qt.AlignCenter)
                    photo_label.setText(Path(photo_path).name.split('.')[0] + "\nCargando...")
                    photo_label.setProperty("original_path", photo_path)
                    photo_label.setProperty("loaded", False)
                    photo_label.doubleClickedPath.connect(self._open_photo_detail)

                    row, col = i // num_cols, i % num_cols
                    photo_grid_layout.addWidget(photo_label, row, col)

                year_main_layout.addWidget(photo_grid_widget)

            self.photo_container_layout.addWidget(year_group_box)
            year_item.setExpanded(True)

        self.photo_container_layout.addStretch(1)
        QTimer.singleShot(100, self._load_main_visible_thumbnails)

    # --- NUEVA FUNCIÓN ---
    def _display_videos(self):
        """Muestra los VÍDEOS agrupados por fecha."""
        while self.video_container_layout.count() > 0:
            item = self.video_container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.video_date_tree_widget.clear()

        self.video_group_widgets = {} # Almacenará { 'year-month': widget }

        viewport_width = self.video_scroll_area.viewport().width() - 30
        thumb_width = THUMBNAIL_SIZE[0] + 10
        num_cols = max(1, viewport_width // thumb_width)

        sorted_years = sorted(self.videos_by_year_month.keys(), reverse=True)

        for year in sorted_years:
            if year == "Sin Fecha": continue
            year_item = QTreeWidgetItem(self.video_date_tree_widget, [str(year)])
            self.video_group_widgets[year] = None

            sorted_months = sorted(self.videos_by_year_month[year].keys())

            year_group_box = QGroupBox(f"Año {year}")
            year_group_box.setObjectName(f"group_{year}")
            year_main_layout = QVBoxLayout(year_group_box)
            self.video_group_widgets[year] = year_group_box

            for month in sorted_months:
                if month == "00": continue
                videos = self.videos_by_year_month[year][month]
                if not videos: continue

                try:
                    month_name = datetime.datetime.strptime(month, "%m").strftime("%B").capitalize()
                except ValueError:
                    month_name = "Mes Desconocido"

                month_item = QTreeWidgetItem(year_item, [f"{month_name} ({len(videos)})"])
                month_item.setData(0, Qt.UserRole, (year, month))

                month_label = QLabel(month_name)
                month_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 10px;")
                year_main_layout.addWidget(month_label)
                self.video_group_widgets[f"{year}-{month}"] = month_label

                video_grid_widget = QWidget()
                video_grid_layout = QGridLayout(video_grid_widget)
                video_grid_layout.setSpacing(5)

                for i, video_path in enumerate(videos):
                    # --- MODIFICADO: Conectamos el doble clic ---
                    video_label = ZoomableClickableLabel(video_path)
                    video_label.is_thumbnail_view = True
                    video_label.setFixedSize(THUMBNAIL_SIZE[0] + 10, THUMBNAIL_SIZE[1] + 25)
                    video_label.setToolTip(video_path)
                    video_label.setAlignment(Qt.AlignCenter)
                    video_label.setText(Path(video_path).name.split('.')[0] + "\nCargando...")
                    video_label.setProperty("original_path", video_path)
                    video_label.setProperty("loaded", False)
                    # Apunta a la nueva función _open_video_player
                    video_label.doubleClickedPath.connect(self._open_video_player) # <-- LÍNEA MODIFICADA

                    row, col = i // num_cols, i % num_cols
                    video_grid_layout.addWidget(video_label, row, col)

                year_main_layout.addWidget(video_grid_widget)

            self.video_container_layout.addWidget(year_group_box)
            year_item.setExpanded(True)

        self.video_container_layout.addStretch(1)
        QTimer.singleShot(100, self._load_visible_video_thumbnails)
    # --- FIN DE LO NUEVO ---

    @Slot(QTreeWidgetItem, QTreeWidgetItem)
    def _scroll_to_item(self, current_item: QTreeWidgetItem, previous_item: QTreeWidgetItem):
        """Desplazarse al grupo de FOTOS seleccionado en el árbol."""
        if not current_item: return
        if current_item.parent():
            year, month = current_item.data(0, Qt.UserRole)
            target_key = f"{year}-{month}"
        else:
            year = current_item.text(0)
            target_key = year

        target_widget = self.photo_group_widgets.get(target_key)
        if target_widget:
            self.scroll_area.ensureWidgetVisible(target_widget, 50, 50)
            QTimer.singleShot(200, self._load_main_visible_thumbnails)

    # --- NUEVA FUNCIÓN ---
    @Slot(QTreeWidgetItem, QTreeWidgetItem)
    def _scroll_to_video_item(self, current_item: QTreeWidgetItem, previous_item: QTreeWidgetItem):
        """Desplazarse al grupo de VÍDEOS seleccionado en el árbol."""
        if not current_item: return
        if current_item.parent():
            year, month = current_item.data(0, Qt.UserRole)
            target_key = f"{year}-{month}"
        else:
            year = current_item.text(0)
            target_key = year

        target_widget = self.video_group_widgets.get(target_key)
        if target_widget:
            self.video_scroll_area.ensureWidgetVisible(target_widget, 50, 50)
            QTimer.singleShot(200, self._load_visible_video_thumbnails)
    # --- FIN DE LO NUEVO ---

    @Slot(dict)
    def _handle_search_finished(self, photos_by_year_month):
        """Se llama cuando el PhotoFinderWorker termina."""
        self.photos_by_year_month = photos_by_year_month
        self.select_dir_button.setEnabled(True) # Reactivar botón
        num_fotos = sum(len(photos) for months in photos_by_year_month.values() for photos in months.values())
        self._set_status(f"Escaneo de fotos finalizado. {num_fotos} fotos encontradas.")
        self._display_photos()

    # --- NUEVA FUNCIÓN ---
    @Slot(dict)
    def _handle_video_search_finished(self, videos_by_year_month):
        """Se llama cuando el VideoFinderWorker termina."""
        self.videos_by_year_month = videos_by_year_month
        self.select_dir_button.setEnabled(True) # Reactivar botón
        num_videos = sum(len(videos) for months in videos_by_year_month.values() for videos in months.values())
        self._set_status(f"Escaneo de vídeos finalizado. {num_videos} vídeos encontrados.")
        self._display_videos()
    # --- FIN DE LO NUEVO ---

    def _set_status(self, message):
        self.status_label.setText(f"Estado: {message}")

    def _load_main_visible_thumbnails(self):
        """Carga miniaturas de FOTOS visibles."""
        viewport = self.scroll_area.viewport()
        preload_rect = viewport.rect().adjusted(0, -PRELOAD_MARGIN_PX, 0, PRELOAD_MARGIN_PX)
        for photo_label in self.scroll_area.widget().findChildren(QLabel):
            original_path = photo_label.property("original_path")
            is_loaded = photo_label.property("loaded")
            if original_path and is_loaded is False:
                label_pos = photo_label.mapTo(viewport, photo_label.rect().topLeft())
                label_rect_in_viewport = photo_label.rect().translated(label_pos)
                if preload_rect.intersects(label_rect_in_viewport):
                    photo_label.setProperty("loaded", None)
                    # --- MODIFICADO: Usar el loader de IMAGEN ---
                    loader = ThumbnailLoader(original_path, self.thumb_signals)
                    # --- FIN DE MODIFICACIÓN ---
                    self.threadpool.start(loader)

    # --- NUEVA FUNCIÓN ---
    def _load_visible_video_thumbnails(self):
        """Carga miniaturas de VÍDEOS visibles."""
        viewport = self.video_scroll_area.viewport()
        preload_rect = viewport.rect().adjusted(0, -PRELOAD_MARGIN_PX, 0, PRELOAD_MARGIN_PX)
        # Buscar en el contenedor de vídeos
        for video_label in self.video_scroll_area.widget().findChildren(QLabel):
            original_path = video_label.property("original_path")
            is_loaded = video_label.property("loaded")
            if original_path and is_loaded is False:
                label_pos = video_label.mapTo(viewport, video_label.rect().topLeft())
                label_rect_in_viewport = video_label.rect().translated(label_pos)
                if preload_rect.intersects(label_rect_in_viewport):
                    video_label.setProperty("loaded", None)
                    # --- MODIFICADO: Usar el loader de VÍDEO ---
                    loader = VideoThumbnailLoader(original_path, self.thumb_signals)
                    # --- FIN DE MODIFICACIÓN ---
                    self.threadpool.start(loader)
    # --- FIN DE LO NUEVO ---

    @Slot()
    def _load_person_visible_thumbnails(self):
        viewport = self.person_photo_scroll_area.viewport()
        preload_rect = viewport.rect().adjusted(0, -PRELOAD_MARGIN_PX, 0, PRELOAD_MARGIN_PX)
        person_photo_widget = self.person_photo_scroll_area.widget()
        if not person_photo_widget:
            return
        for photo_label in person_photo_widget.findChildren(ZoomableClickableLabel):
            original_path = photo_label.property("original_path")
            is_loaded = photo_label.property("loaded")
            if original_path and is_loaded is False:
                label_pos = photo_label.mapTo(viewport, photo_label.rect().topLeft())
                label_rect_in_viewport = photo_label.rect().translated(label_pos)
                if preload_rect.intersects(label_rect_in_viewport):
                    photo_label.setProperty("loaded", None)
                    # --- MODIFICADO: Usar el loader de IMAGEN ---
                    loader = ThumbnailLoader(original_path, self.thumb_signals)
                    # --- FIN DE MODIFICACIÓN ---
                    self.threadpool.start(loader)

    @Slot(str, QPixmap)
    def _update_thumbnail(self, original_path: str, pixmap: QPixmap):
        def update_in_container(container_widget):
            if not container_widget:
                return
            for label in container_widget.findChildren(ZoomableClickableLabel):
                if label.property("original_path") == original_path and label.property("loaded") is not True:
                    label.setPixmap(pixmap.scaled(THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1], Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    label.setText("")
                    label.setProperty("loaded", True)

        # Update all matching labels in the "Fotos" tab
        update_in_container(self.scroll_area.widget())
        # --- NUEVO: Actualizar la pestaña de vídeos también ---
        update_in_container(self.video_scroll_area.widget())
        # --- FIN DE LO NUEVO ---
        # Update all matching labels in the "Personas" tab
        update_in_container(self.person_photo_scroll_area.widget())

    @Slot(str)
    def _handle_thumbnail_failed(self, original_path: str):
        def fail_in_container(container_widget):
            if not container_widget:
                return
            for label in container_widget.findChildren(ZoomableClickableLabel):
                if label.property("original_path") == original_path and label.property("loaded") is not True:
                    label.setText("Error al cargar.")
                    label.setProperty("loaded", True)

        fail_in_container(self.scroll_area.widget())
        # --- NUEVO ---
        fail_in_container(self.video_scroll_area.widget())
        # --- FIN DE LO NUEVO ---
        fail_in_container(self.person_photo_scroll_area.widget())

    @Slot()
    def _save_photo_splitter_state(self):
        """Guarda las posiciones del splitter de FOTOS en la configuración."""
        sizes = self.main_splitter.sizes()
        config_data = config_manager.load_config()
        config_data['photo_splitter_sizes'] = sizes
        config_manager.save_config(config_data)

    # --- NUEVA FUNCIÓN ---
    @Slot()
    def _save_video_splitter_state(self):
        """Guarda las posiciones del splitter de VÍDEOS en la configuración."""
        sizes = self.video_splitter.sizes()
        config_data = config_manager.load_config()
        config_data['video_splitter_sizes'] = sizes
        config_manager.save_config(config_data)
    # --- FIN DE LO NUEVO ---

    def _load_photo_splitter_state(self):
        """Carga las posiciones del splitter de FOTOS desde la configuración."""
        config_data = config_manager.load_config()
        sizes = config_data.get('photo_splitter_sizes')
        min_right_width = 180
        if sizes and len(sizes) == 2:
            if sizes[1] < min_right_width:
                sizes[0] = sizes[0] + (sizes[1] - min_right_width)
                sizes[1] = min_right_width
            self.main_splitter.setSizes(sizes)
        else:
            default_width = self.width()
            default_sizes = [int(default_width * 0.8), int(default_width * 0.2)]
            if default_sizes[1] < min_right_width:
                 default_sizes[1] = min_right_width
                 default_sizes[0] = default_width - min_right_width
            self.main_splitter.setSizes(default_sizes)

    # --- NUEVA FUNCIÓN ---
    def _load_video_splitter_state(self):
        """Carga las posiciones del splitter de VÍDEOS desde la configuración."""
        config_data = config_manager.load_config()
        sizes = config_data.get('video_splitter_sizes')
        min_right_width = 180
        if sizes and len(sizes) == 2:
            if sizes[1] < min_right_width:
                sizes[0] = sizes[0] + (sizes[1] - min_right_width)
                sizes[1] = min_right_width
            self.video_splitter.setSizes(sizes)
        else:
            default_width = self.width()
            default_sizes = [int(default_width * 0.8), int(default_width * 0.2)]
            if default_sizes[1] < min_right_width:
                 default_sizes[1] = min_right_width
                 default_sizes[0] = default_width - min_right_width
            self.video_splitter.setSizes(default_sizes)
    # --- FIN DE LO NUEVO ---

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)

    @Slot()
    def _handle_resize_timeout(self):
        # Si no hay fotos O vídeos cargados, no hagas nada
        if not self.photos_by_year_month and not self.videos_by_year_month:
            return

        print(f"Redibujando layout para el nuevo ancho.")
        # Re-dibujar AMBAS pestañas
        if self.photos_by_year_month:
            self._display_photos()
        if self.videos_by_year_month:
            self._display_videos()

    @Slot(str)
    def _open_photo_detail(self, original_path):
        """Abre la ventana de detalle de la foto."""
        self._set_status(f"Abriendo detalle para: {Path(original_path).name}")
        dialog = PhotoDetailDialog(original_path, self.db, self)
        dialog.metadata_changed.connect(self._handle_photo_date_changed)
        dialog.exec()
        self._set_status("Detalle cerrado.")

    @Slot()
    def _handle_photo_date_changed(self, photo_path: str, new_year: str, new_month: str):
        self._set_status("Metadatos de foto cambiados. Reconstruyendo vista...")
        path_found_and_removed = False
        for year, months in self.photos_by_year_month.items():
            for month, photos in months.items():
                if photo_path in photos:
                    photos.remove(photo_path)
                    path_found_and_removed = True
                    if not photos:
                        del self.photos_by_year_month[year][month]
                    if not self.photos_by_year_month[year]:
                        del self.photos_by_year_month[year]
                    break
            if path_found_and_removed:
                break
        if new_year not in self.photos_by_year_month:
            self.photos_by_year_month[new_year] = {}
        if new_month not in self.photos_by_year_month[new_year]:
            self.photos_by_year_month[new_year][new_month] = []
        self.photos_by_year_month[new_year][new_month].append(photo_path)
        self._display_photos()

    @Slot(str)
    def _open_video_player(self, video_path):
        """
        Abre el archivo de vídeo dado con el reproductor por defecto del sistema.
        """
        try:
            # Convertir la ruta del archivo (ej: /home/user/video.mp4)
            # a una URL de archivo (ej: file:///home/user/video.mp4)
            file_url = QUrl.fromLocalFile(video_path)

            # Pedir a QDesktopServices que abra la URL
            if not QDesktopServices.openUrl(file_url):
                # Si falla, mostrar un error
                self._set_status(f"Error: No se pudo abrir {video_path}. ¿Hay un reproductor de vídeo configurado?")
            else:
                self._set_status(f"Abriendo {Path(video_path).name}...")
        except Exception as e:
            print(f"Error al intentar abrir el vídeo: {e}")
            self._set_status(f"Error: {e}")

    @Slot(int)
    def _on_tab_changed(self, index):
        """
        Se llama cuando el usuario cambia de pestaña (Fotos <-> Personas).
        """
        tab_name = self.tab_widget.tabText(index)

        # La lógica de escaneo de caras solo se activa al pulsar "Personas"
        if tab_name == "Personas":
            self._set_status("Cargando vista de personas...")
            self._load_people_list()
            if self.face_scan_thread and self.face_scan_thread.isRunning():
                self._set_status("Escaneo de caras en curso...")
                return
            while self.unknown_faces_layout.count() > 0:
                item = self.unknown_faces_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            self.current_face_count = 0
            if self.face_loading_label:
                self.face_loading_label.deleteLater()
                self.face_loading_label = None
            self._load_existing_faces_async()
            self._start_face_scan()

    def _load_people_list(self):
        self.people_tree_widget.clear()
        unknown_item = QTreeWidgetItem(self.people_tree_widget, ["Caras Sin Asignar"])
        unknown_item.setData(0, Qt.UserRole, -1)
        deleted_item = QTreeWidgetItem(self.people_tree_widget, ["Caras Eliminadas"])
        deleted_item.setData(0, Qt.UserRole, -2)
        people = self.db.get_all_people()
        if people:
            people_root_item = QTreeWidgetItem(self.people_tree_widget, ["Personas"])
            for person_row in people:
                person_id = person_row['id']
                person_name = person_row['name']
                person_item = QTreeWidgetItem(people_root_item, [person_name])
                person_item.setData(0, Qt.UserRole, person_id)
            people_root_item.setExpanded(True)
        self.people_tree_widget.setCurrentItem(unknown_item)

    def _populate_face_grid_async(self, face_list: list, is_deleted_view: bool = False):
        while self.unknown_faces_layout.count() > 0:
            item = self.unknown_faces_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.current_face_count = 0
        if not face_list:
            placeholder = QLabel("No se han encontrado caras.")
            placeholder.setAlignment(Qt.AlignCenter)
            self.unknown_faces_layout.addWidget(placeholder, 0, 0, Qt.AlignCenter)
            return
        self.current_face_count = len(face_list)
        viewport_width = self.left_people_stack.width() - 30
        num_cols = max(1, viewport_width // 110)
        for i, face_row in enumerate(face_list):
            face_id = face_row['id']
            face_widget = CircularFaceLabel(QPixmap())
            face_widget.setText("...")
            face_widget.setProperty("face_id", face_id)
            face_widget.setProperty("is_deleted_view", is_deleted_view)
            face_widget.rightClicked.connect(self._on_face_right_clicked)
            face_widget.clicked.connect(self._on_face_clicked)
            row, col = i // num_cols, i % num_cols
            self.unknown_faces_layout.addWidget(face_widget, row, col, Qt.AlignTop)
            loader = FaceLoader(
                self.face_loader_signals,
                face_id,
                face_row['filepath'],
                face_row['location']
            )
            self.threadpool.start(loader)

    def _load_existing_faces_async(self):
        self.unknown_faces_group.setTitle("Caras Sin Asignar")
        self.cluster_faces_button.setEnabled(True)
        self.show_deleted_faces_button.setEnabled(True)
        unknown_faces = self.db.get_unknown_faces()
        self._populate_face_grid_async(unknown_faces, is_deleted_view=False)

    @Slot()
    def _on_face_clicked(self):
        sender_widget = self.sender()
        if not sender_widget:
            return
        is_deleted_view = sender_widget.property("is_deleted_view")
        face_id = sender_widget.property("face_id")
        photo_path = sender_widget.property("photo_path")
        if not face_id or not photo_path:
            print("Clic en una cara que aún no tiene datos (cargando).")
            return
        self._set_status(f"Etiquetando Cara ID: {face_id}...")
        dialog = FaceClusterDialog(
            self.db,
            self.threadpool,
            [face_id],
            self
        )
        result = dialog.exec()
        if result == QDialog.Accepted:
            self._set_status("Cara etiquetada. Refrescando...")
            self._load_people_list()
            if is_deleted_view:
                self._show_deleted_faces()
            else:
                self._load_existing_faces_async()
        elif result == FaceClusterDialog.DeleteRole:
            self._set_status("Cara eliminada. Refrescando...")
            if is_deleted_view:
                self._show_deleted_faces()
            else:
                self._load_existing_faces_async()
        else:
            self._set_status("Etiquetado cancelado.")

    @Slot(QPoint)
    def _on_face_right_clicked(self, pos):
        sender_widget = self.sender()
        if not sender_widget:
            return
        face_id = sender_widget.property("face_id")
        is_deleted_view = sender_widget.property("is_deleted_view")
        menu = QMenu(self)
        if is_deleted_view:
            restore_action = menu.addAction("Restaurar cara")
            restore_action.triggered.connect(lambda: self._restore_face(face_id, sender_widget))
        else:
            delete_action = menu.addAction("Eliminar cara reconocida")
            delete_action.triggered.connect(lambda: self._delete_face(face_id, sender_widget))
        menu.exec(pos)

    def _delete_face(self, face_id: int, widget: QWidget):
        self.db.soft_delete_face(face_id)
        widget.deleteLater()
        self._set_status(f"Cara ID {face_id} eliminada.")
        self._load_existing_faces_async()

    def _restore_face(self, face_id: int, widget: QWidget):
        self.db.restore_face(face_id)
        widget.deleteLater()
        self._set_status(f"Cara ID {face_id} restaurada.")
        self._show_deleted_faces()

    @Slot()
    def _show_deleted_faces(self):
        self.left_people_stack.setCurrentIndex(0)
        self.unknown_faces_group.setTitle("Caras Eliminadas")
        self.cluster_faces_button.setEnabled(False)
        self.show_deleted_faces_button.setEnabled(False)
        deleted_faces = self.db.get_deleted_faces()
        self._populate_face_grid_async(deleted_faces, is_deleted_view=True)
        self._set_status(f"Mostrando {len(deleted_faces)} caras eliminadas.")

    @Slot(QTreeWidgetItem, QTreeWidgetItem)
    def _on_person_selected(self, current_item: QTreeWidgetItem, previous_item: QTreeWidgetItem):
        if not current_item:
            return
        person_id = current_item.data(0, Qt.UserRole)
        if person_id == -1:
            self.left_people_stack.setCurrentIndex(0)
            self._load_existing_faces_async()
        elif person_id == -2:
            self.left_people_stack.setCurrentIndex(0)
            self._show_deleted_faces()
        elif person_id >= 0:
            self.left_people_stack.setCurrentIndex(1)
            person_name = current_item.text(0)
            self._load_photos_for_person(person_id, person_name)

    @Slot(int)
    def _update_face_scan_percentage(self, percentage):
        if not self.face_loading_label:
            self.face_loading_label = QLabel(f"Buscando caras de personas... {percentage}%")
            self.face_loading_label.setAlignment(Qt.AlignCenter)
            self.face_loading_label.setStyleSheet("font-size: 14pt;")
            self.face_container_layout.insertWidget(1, self.face_loading_label, 0, Qt.AlignCenter)
        else:
            self.face_loading_label.setText(f"Buscando caras de personas... {percentage}%")

    @Slot(int, str, str)
    def _handle_face_found(self, face_id: int, photo_path: str, location_str: str):
        loader = FaceLoader(
            self.face_loader_signals,
            face_id,
            photo_path,
            location_str
        )
        self.threadpool.start(loader)

    @Slot()
    def _handle_scan_finished(self):
        if self.face_loading_label:
            self.face_loading_label.deleteLater()
            self.face_loading_label = None
        if self.current_face_count == 0:
            placeholder = QLabel("No se han encontrado caras.")
            placeholder.setAlignment(Qt.AlignCenter)
            self.unknown_faces_layout.addWidget(placeholder, 0, 0, Qt.AlignCenter)

    @Slot()
    def _on_scan_thread_finished(self):
        """Slot de limpieza para el hilo de FOTOS."""
        if self.photo_thread:
            self.photo_thread.deleteLater()
        self.photo_thread = None
        self.photo_worker = None

    # --- NUEVA FUNCIÓN ---
    @Slot()
    def _on_video_scan_thread_finished(self):
        """Slot de limpieza para el hilo de VÍDEOS."""
        if self.video_thread:
            self.video_thread.deleteLater()
        self.video_thread = None
        self.video_worker = None
    # --- FIN DE LO NUEVO ---

    @Slot()
    def _on_face_scan_thread_finished(self):
        self.face_scan_thread = None
        self.face_scan_worker = None

    @Slot(int, QPixmap, str)
    def _handle_face_loaded(self, face_id: int, pixmap: QPixmap, photo_path: str):
        placeholder = None
        for i in range(self.unknown_faces_layout.count()):
            widget = self.unknown_faces_layout.itemAt(i).widget()
            if widget and widget.property("face_id") == face_id:
                placeholder = widget
                break
        if placeholder:
            placeholder.setPixmap(pixmap)
            placeholder.setText("")
            placeholder.setProperty("photo_path", photo_path)
        else:
            if self.unknown_faces_group.title() != "Caras Sin Asignar":
                return
            face_widget = CircularFaceLabel(pixmap)
            face_widget.setProperty("face_id", face_id)
            face_widget.setProperty("photo_path", photo_path)
            face_widget.setProperty("is_deleted_view", False)
            face_widget.clicked.connect(self._on_face_clicked)
            face_widget.rightClicked.connect(self._on_face_right_clicked)
            num_cols = max(1, (self.face_scroll_area.viewport().width() - 30) // 110)
            row = self.current_face_count // num_cols
            col = self.current_face_count % num_cols
            self.unknown_faces_layout.addWidget(face_widget, row, col, Qt.AlignTop)
            self.current_face_count += 1

    @Slot(int)
    def _handle_face_load_failed(self, face_id: int):
        placeholder = None
        for i in range(self.unknown_faces_layout.count()):
            widget = self.unknown_faces_layout.itemAt(i).widget()
            if widget and widget.property("face_id") == face_id:
                placeholder = widget
                break
        if placeholder:
            placeholder.setText("Error")

    def closeEvent(self, event):
        """Limpia de forma segura todos los hilos antes de salir."""
        print("Cerrando aplicación... Por favor, espere.")
        self._set_status("Cerrando... esperando a que terminen las tareas de fondo.")

        # 1. Detener el hilo de escaneo de fotos
        if self.photo_thread and self.photo_thread.isRunning():
            print("Deteniendo el hilo de escaneo de fotos...")
            if self.photo_worker:
                self.photo_worker.is_running = False
                try: self.photo_worker.finished.disconnect()
                except RuntimeError: pass
            self.photo_thread.quit()
            self.photo_thread.wait(3000)

        # 2. Detener el hilo de escaneo de vídeos (NUEVO)
        if self.video_thread and self.video_thread.isRunning():
            print("Deteniendo el hilo de escaneo de vídeos...")
            if self.video_worker:
                self.video_worker.is_running = False
                try: self.video_worker.finished.disconnect()
                except RuntimeError: pass
            self.video_thread.quit()
            self.video_thread.wait(3000)

        # 3. Detener el hilo de escaneo de caras
        if self.face_scan_thread and self.face_scan_thread.isRunning():
            print("Deteniendo el hilo de escaneo de caras...")
            if self.face_scan_worker:
                self.face_scan_worker.is_running = False
                try: self.face_scan_worker.signals.scan_finished.disconnect()
                except RuntimeError: pass
            self.face_scan_thread.quit()
            self.face_scan_thread.wait(3000)

        # 4. Esperar al pool de QRunnables
        print("Esperando tareas del ThreadPool (miniaturas/caras)...")
        self.threadpool.clear()
        self.threadpool.waitForDone(3000)

        print("Todos los hilos finalizados. Saliendo.")
        event.accept()

    @Slot()
    def _start_clustering(self):
        self.cluster_faces_button.setText("Procesando...")
        self.cluster_faces_button.setEnabled(False)
        self._set_status("Iniciando búsqueda de duplicados...")
        worker = ClusterWorker(self.cluster_signals, self.db)
        self.threadpool.start(worker)

    @Slot(list)
    def _handle_clusters_found(self, clusters: list):
        if not clusters:
            self._set_status("No se encontraron nuevos duplicados.")
            return
        self.cluster_queue = clusters
        self._set_status(f"¡Encontrados {len(self.cluster_queue)} grupos! Procesando...")
        self._process_cluster_queue()

    @Slot()
    def _handle_clustering_finished(self):
        self.cluster_faces_button.setText("Buscar Duplicados")
        self.cluster_faces_button.setEnabled(True)
        if not self.cluster_queue:
             self._set_status("Búsqueda de duplicados finalizada. No se encontraron grupos.")

    @Slot()
    def _process_cluster_queue(self):
        if not self.cluster_queue:
            self._set_status("¡Etiquetado de grupos completado!")
            self._load_existing_faces_async()
            return
        next_cluster_ids = self.cluster_queue.pop(0)
        self._set_status(f"Procesando grupo... quedan {len(self.cluster_queue)} grupos.")
        dialog = FaceClusterDialog(
            self.db,
            self.threadpool,
            next_cluster_ids,
            self
        )
        result = dialog.exec()
        if result == QDialog.Accepted:
            print(f"Grupo guardado. Quedan {len(self.cluster_queue)}.")
            self._load_people_list()
        elif result == FaceClusterDialog.SkipRole:
            print(f"Grupo omitido. Quedan {len(self.cluster_queue)}.")
        elif result == FaceClusterDialog.DeleteRole:
            print(f"Grupo eliminado. Quedan {len(self.cluster_queue)}.")
        else:
            print("Cancelado el etiquetado de grupos.")
            self.cluster_queue = []
            self._set_status("Etiquetado cancelado.")
            self._load_existing_faces_async()
            return
        QTimer.singleShot(100, self._process_cluster_queue)

    def _load_photos_for_person(self, person_id: int, person_name: str):
        self._set_status(f"Mostrando caras de {person_name}.")
        self.cluster_faces_button.setEnabled(False)
        self.show_deleted_faces_button.setEnabled(True)
        person_photos = self.db.get_faces_for_person(person_id)
        self._display_person_photos(person_photos, person_name)


    def _display_person_photos(self, photos_list: list, person_name: str):
        while self.person_photo_layout.count() > 0:
            item = self.person_photo_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if not photos_list:
            placeholder = QLabel(f"No se encontraron fotos para {person_name}.")
            placeholder.setAlignment(Qt.AlignCenter)
            self.person_photo_layout.addWidget(placeholder)
            return
        photos_by_year_month = {}
        for row in photos_list:
            path, year, month = row['filepath'], row['year'], row['month']
            if year not in photos_by_year_month:
                photos_by_year_month[year] = {}
            if month not in photos_by_year_month[year]:
                photos_by_year_month[year][month] = []
            if path not in photos_by_year_month[year][month]:
                photos_by_year_month[year][month].append(path)
        viewport_width = self.left_people_stack.width() - 30
        thumb_width = THUMBNAIL_SIZE[0] + 10
        num_cols = max(1, viewport_width // thumb_width)
        sorted_years = sorted(photos_by_year_month.keys(), reverse=True)
        for year in sorted_years:
            sorted_months = sorted(photos_by_year_month[year].keys(), reverse=True)
            for month in sorted_months:
                photos = photos_by_year_month[year][month]
                if not photos: continue
                try:
                    month_name = datetime.datetime.strptime(month, "%m").strftime("%B").capitalize()
                except ValueError:
                    month_name = "Mes Desconocido"
                group_label = QLabel(f"{month_name} {year}")
                group_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 10px;")
                self.person_photo_layout.addWidget(group_label)
                photo_grid_widget = QWidget()
                photo_grid_layout = QGridLayout(photo_grid_widget)
                photo_grid_layout.setSpacing(5)
                for i, photo_path in enumerate(photos):
                    photo_label = ZoomableClickableLabel(photo_path)
                    photo_label.is_thumbnail_view = True
                    photo_label.setFixedSize(THUMBNAIL_SIZE[0] + 10, THUMBNAIL_SIZE[1] + 25)
                    photo_label.setToolTip(photo_path)
                    photo_label.setAlignment(Qt.AlignCenter)
                    photo_label.setText(Path(photo_path).name.split('.')[0] + "\nCargando...")
                    photo_label.setProperty("original_path", photo_path)
                    photo_label.setProperty("loaded", False)
                    photo_label.doubleClickedPath.connect(self._open_photo_detail)
                    row, col = i // num_cols, i % num_cols
                    photo_grid_layout.addWidget(photo_label, row, col)
                self.person_photo_layout.addWidget(photo_grid_widget)
        self.person_photo_layout.addStretch(1)
        QTimer.singleShot(100, self._load_person_visible_thumbnails)

def run_visagevault():
    """Función para iniciar la aplicación gráfica."""
    app = QApplication(sys.argv)
    window = VisageVaultApp()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_visagevault()
