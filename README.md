<p align="center">
  <img src="https://github.com/danitxu79/visagevault/raw/master/visagevault.png" alt="Logo de VisageVault">
</p>


-----

# VisageVault - Gestor de Fotografías Inteligente

[](https://www.google.com/search?q=https://github.com/danitxu79/VisageVault)
[](https://www.google.com/search?q=LICENSE)

VisageVault es una aplicación de escritorio para macOS, Windows y Linux, diseñada para organizar y explorar grandes colecciones de fotos **y vídeos**. Su característica principal es el **reconocimiento facial** (en fotos), que permite escanear, agrupar y etiquetar personas automáticamente en tu biblioteca.

## ✨ Características Principales

  * **Escaneo de Directorios:** Analiza recursivamente tu carpeta de medios para encontrar todas las imágenes (`.jpg`, `.png`, etc.) **y vídeos** (`.mp4`, `.mkv`, `.mov`, etc.).
  * **Organización por Fecha:** Agrupa automáticamente las fotos y vídeos por Año y Mes, leyendo los metadatos EXIF o la fecha de archivo.
  * **Soporte de Vídeo Dedicado:** Una pestaña separada para navegar por tus vídeos, con generación de miniaturas (usando OpenCV) y reproducción mediante doble clic (abre el reproductor predeterminado del sistema).
  * **Soporte RAW:** **Visualización y reconocimiento facial en formatos RAW comunes (.NEF, .CR2, etc.)**.
  * **Detección de Caras (en Fotos):** Utiliza `face_recognition` para escanear cada foto y detectar todas las caras presentes.
  * **Agrupamiento (Clustering):** Compara todas las caras "Desconocidas" y las agrupa (usando `sklearn.cluster.DBSCAN`) para sugerir personas que son la misma.
  * **Etiquetado Sencillo:** Una interfaz dedicada para revisar las caras agrupadas y asignarles un nombre.
  * **Navegación por Persona:** Una vez etiquetadas, puedes ver todas las fotos en las que aparece una persona específica.
  * **Gestión de Metadatos:** Permite editar la fecha (Año/Mes) de las fotos si los metadatos son incorrectos, **guardando el cambio permanentemente en el archivo (EXIF/Fecha de Archivo)**.
  * **Gestión de Archivos:** **Menú contextual para Ocultar/Restaurar archivos de la vista o Eliminarlos permanentemente del disco.**
  * **Selección Mejorada:** **Soporte de selección de rango (Shift + Clic) y por arrastre (cuadro de selección).**
  * **Caché de Miniaturas:** Genera y almacena miniaturas para fotos y vídeos para una carga y navegación ultra rápidas.**

-----

## 🛠️ Requisitos

Para ejecutar VisageVault desde el código fuente, necesitarás Python 3.11+ y varias dependencias del sistema.

### 1\. Dependencias del Sistema

Las librerías de Python necesitan compilar código C++ y acceder a códecs de vídeo.

  * **En Debian/Ubuntu:**
    ```bash
    sudo apt install build-essential cmake libopenblas-dev liblapack-dev ffmpeg
    ```
  * **En Arch/Manjaro:**
    ```bash
    sudo pacman -S base-devel cmake openblas lapack ffmpeg
    ```
  * **En Fedora:**
    ```bash
    sudo dnf groupinstall "Development Tools"
    sudo dnf install cmake openblas-devel lapack-devel ffmpeg
    ```

### 2\. Dependencias de Python

Todos los paquetes de Python necesarios están listados en `requirements.txt`. Los principales son:

  * `PySide6` (Para la interfaz gráfica Qt 6)
  * `face_recognition` (Para la detección de caras)
  * `scikit-learn` (Para el clustering de caras)
  * `Pillow` (Para el manejo de imágenes)
  * `piexif` **(Para leer y escribir metadatos EXIF, ahora usado para la persistencia)**
  * `rawpy` **(Nuevo - Para el soporte de archivos RAW)**
  * `opencv-python-headless` (¡Nuevo\! Para la generación de miniaturas de vídeo)**

-----

## 🚀 Instalación (desde código fuente)

1.  **Clona el repositorio:**

    ```bash
    git clone [https://github.com/danitxu79/VisageVault.git](https://github.com/danitxu79/VisageVault.git)
    cd VisageVault
    ```

2.  **Instala las Dependencias del Sistema:**

      * Asegúrate de haber instalado las herramientas de compilación (`cmake`, `ffmpeg`, etc.) mencionadas en la sección "Requisitos".

3.  **Crea un entorno virtual:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Instala los requisitos de Python:**

      * (Este paso puede tardar varios minutos, ya que compilará `dlib` y `numpy`).

    ```bash
    pip install -r requirements.txt
    ```

-----

## 🏃 Ejecución

Una vez que todo esté instalado, puedes ejecutar la aplicación:

```bash
# Activa el entorno virtual (si no lo has hecho)
source venv/bin/activate

# Inicia la aplicación
python visagevault.py
````

La primera vez que la ejecutes, te pedirá que selecciones el directorio raíz que contiene tus fotos y vídeos.

-----

## 📦 Compilación (AppImage para Linux)

Este repositorio incluye un script `compila.sh` que automatiza la creación de una AppImage autocontenida usando **PyInstaller** y **linuxdeploy**.

Este script maneja los pasos complejos de empaquetado, incluyendo las importaciones ocultas (`--hidden-import`) de `numpy`, `sklearn` y `scipy`.

### Requisitos para la Compilación

Además de los requisitos de ejecución, para compilar la AppImage necesitarás:

1.  **Herramientas de Qt6:** `linuxdeploy` las necesita para empaquetar los plugins de la plataforma Qt.
      * **En Arch/Manjaro:** `sudo pacman -S qt6-tools`
      * **En Debian/Ubuntu:** `sudo apt install qt6-base-dev`
2.  **Herramientas de AppImage:**
    ```bash
    wget [https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage](https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage)
    chmod +x linuxdeploy-x86_64.AppImage
    ```
3.  **pyenv (Recomendado):** El script está configurado para usar `pyenv local 3.11.9` para asegurar una compilación consistente.

### Compilar

Simplemente ejecuta el script de compilación:

```bash
./compila.sh
```

Si todo sale bien, encontrarás el archivo `VisageVault-x86_64.AppImage` listo para distribuir y ejecutar.

-----

## 📜 Licencia

Este proyecto se ofrece bajo un modelo de **Doble Licencia (Dual License)**:

1.  **LGPLv3:** Ideal para proyectos de código abierto. Si usas esta biblioteca (especialmente si la modificas), debes cumplir con las obligaciones de la LGPLv3.
2.  **Comercial (Privativa):** Si los términos de la LGPLv3 no se ajustan a tus necesidades (por ejemplo, para software propietario de código cerrado), por favor contacta al autor para adquirir una licencia comercial.

Para más detalles, consulta el archivo `LICENSE` o la cabecera de `visagevault.py`.
