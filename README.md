# 📸 VisageVault - Gestor de Fotografías Inteligente

## Visión General

**VisageVault** es un gestor de colecciones fotográficas avanzado, diseñado para el entorno Linux (y portable a Windows/macOS), que utiliza la inteligencia artificial para automatizar la organización, la búsqueda y la gestión de metadatos.

En esta fase de desarrollo (v0.1), la aplicación se centra en la estabilidad, la gestión de archivos en colecciones masivas y la edición persistente de metadatos de tiempo.

---

## 🚀 Características Clave (v0.1 Pre-Release)

* **Organización Automática por Año:** Las fotografías se agrupan automáticamente por año utilizando una jerarquía robusta (EXIF > Nombre de Archivo > Fecha de Modificación).
* **Actualización Persistente de Años:** El año de una fotografía es editable directamente en el visor de detalles y se guarda en una base de datos local (`SQLite`), asegurando que la foto se mueva a la agrupación correcta en la interfaz.
* **Visor de Detalles Avanzado:** Ventana modal con `QSplitter` vertical, permitiendo la visualización de la imagen a tamaño completo con **zoom por rueda del ratón** y la edición rápida de metadatos.
* **Experiencia Fluida:** Interfaz gráfica basada en **PySide6 (Qt)** con **precarga asíncrona** de miniaturas y gestión de hilos para evitar que la interfaz se congele durante el escaneo de directorios.

---

## 💻 Requisitos del Sistema

* **Sistema Operativo:** Linux (Probado en Bash/Desktop Environment).
* **Python:** Versión 3.9 o superior.
* **Hardware:** Se recomienda al menos 4 GB de RAM para el procesamiento de imágenes.

### Instalación de Dependencias

Se requiere un entorno virtual (`venv`) para aislar las dependencias del sistema:

```bash
# Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar las librerías principales
pip install PySide6 Pillow piexif
