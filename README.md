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


### Instalación de Dependencias


## 📜 Licencia

Este proyecto se ofrece bajo un modelo de Doble Licencia (Dual License), brindando máxima flexibilidad:

1. Licencia Pública (LGPLv3)

Este software está disponible bajo la GNU Lesser General Public License v3.0 (LGPLv3).
Puedes usarlo libremente de acuerdo con los términos de la LGPLv3, lo cual es ideal para proyectos de código abierto. En resumen, esto significa que si usas esta biblioteca (especialmente si la modificas), debes cumplir con las obligaciones de la LGPLv3, como publicar el código fuente de tus modificaciones a esta biblioteca y permitir que los usuarios la reemplacen.
Puedes encontrar el texto completo de la licencia en el archivo LICENSE de este repositorio.

2. Licencia Comercial (Privativa)

Si los términos de la LGPLv3 no se ajustan a tus necesidades, ofrezco una licencia comercial alternativa.
Necesitarás una licencia comercial si, por ejemplo:

    Deseas incluir el código en un software propietario (código cerrado) sin tener que publicar tus modificaciones.
    Necesitas enlazar estáticamente (static linking) la biblioteca con tu aplicación propietaria.
    Prefieres no estar sujeto a las obligaciones y restricciones de la LGPLv3.

La licencia comercial te otorga el derecho a usar el código en tus aplicaciones comerciales de código cerrado sin las restricciones de la LGPLv3, a cambio de una tarifa.
Para adquirir una licencia comercial o para más información, por favor, pónte en contacto conmigo en:

dani.eus79@gmail.com


## ✉️ Contacto

Creado por **Daniel Serrano Armenta**

* `dani.eus79@gmail.com`
* Encuéntrame en GitHub: `@danitxu79`
* Portafolio: `https://danitxu79.github.io/`
