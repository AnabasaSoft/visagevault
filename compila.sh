#!/bin/bash

# ==============================================================================
# SCRIPT DE BUILD DE APPIMAGE PARA VisageVault (v3)
# ==============================================================================
#
# Corrige el error 'ModuleNotFoundError: No module named 'sklearn._cyutility''
#
# ==============================================================================

# --- Configuración Inicial ---
set -e
set -x

# --- Verificaciones Previas ---
echo "--- Verificando archivos necesarios ---"
if [ ! -f "visagevault.py" ]; then
    echo "Error: No se encuentra 'visagevault.py'. Asegúrate de estar en el directorio correcto."
    exit 1
fi
if [ ! -f "requirements.txt" ]; then
    echo "Error: No se encuentra 'requirements.txt'."
    exit 1
fi
if [ ! -f "visagevault.png" ]; then
    echo "Error: No se encuentra 'visagevault.png'."
    exit 1
fi
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    echo "Error: No se encuentra 'linuxdeploy-x86_64.AppImage'. Descárgalo en este directorio."
    exit 1
fi

echo "NOTA: Asegúrate de que 'visagevault.png' sea un icono CUADRADO (ej: 256x256 o 512x512)."
echo "Presiona Enter para continuar o Ctrl+C para cancelar y arreglar el icono..."
read

# --- PASO 1: Limpiar builds anteriores ---
echo "--- PASO 1: Limpiando builds anteriores ---"
rm -rf dist build AppDir VisageVault-x86_64.AppImage

# --- PASO 2: Configurar Entorno e Instalar Dependencias ---
echo "--- PASO 2: Configurando entorno e instalando dependencias ---"
pyenv local 3.11.9
pip install -r requirements.txt

# --- PASO 3: Ejecutar PyInstaller (con todas las correcciones) ---
echo "--- PASO 3: Ejecutando PyInstaller ---"
pyinstaller --noconfirm \
            --onedir \
            --windowed \
            --name VisageVault \
            --add-data="visagevault.png:." \
            --collect-data face_recognition_models \
            --hidden-import=numpy \
            --hidden-import=sklearn \
            --hidden-import=scipy._cyutility \
            --hidden-import=sklearn._cyutility \
            visagevault.py

# --- PASO 4: Crear la estructura de AppDir ---
echo "--- PASO 4: Creando la estructura de AppDir ---"
mkdir -p AppDir/usr/bin
cp -r dist/VisageVault/* AppDir/usr/bin/
cp visagevault.png AppDir/

# --- PASO 5: Crear el archivo .desktop ---
echo "--- PASO 5: Creando archivo .desktop ---"
cat << EOF > AppDir/visagevault.desktop
[Desktop Entry]
Name=VisageVault
Comment=Gestor de Fotografías Inteligente
Exec=VisageVault
Icon=visagevault
Type=Application
Categories=Graphics;Photography;
EOF

# --- PASO 6: Ejecutar linuxdeploy ---
echo "--- PASO 6: Ejecutando linuxdeploy para construir la AppImage ---"
./linuxdeploy-x86_64.AppImage --appdir AppDir \
                             --desktop-file AppDir/visagevault.desktop \
                             --icon-file AppDir/visagevault.png \
                             --output appimage

# --- FINALIZADO ---
echo "------------------------------------------------"
echo "¡ÉXITO! La AppImage se ha creado:"
ls -l VisageVault-x86_64.AppImage
echo "------------------------------------------------"
echo "Prueba a ejecutarla con:"
echo "./VisageVault-x86_64.AppImage"
