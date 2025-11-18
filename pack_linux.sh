#!/bin/bash

# Este script utiliza fpm para crear paquetes .deb y .rpm
# a partir del ejecutable de PyInstaller.

# La versión es pasada por GitHub Actions como argumento ($1)
VERSION=$1
if [ -z "$VERSION" ]; then
    echo "ERROR: La versión no fue especificada."
    exit 1
fi

# El directorio de PyInstaller debe existir
PYINSTALLER_DIR="dist"
if [ ! -d "$PYINSTALLER_DIR" ]; then
    echo "ERROR: Directorio de PyInstaller 'dist/' no encontrado."
    exit 1
fi

EXECUTABLE_PATH="$PYINSTALLER_DIR/VisageVault"
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "ERROR: Ejecutable de PyInstaller no encontrado: $EXECUTABLE_PATH"
    exit 1
fi

echo "--- 📦 Creando paquetes DEB y RPM (fpm) ---"

# --- CONFIGURACIÓN ---
APP_NAME="visagevault"
APP_DESCRIPTION="Gestor de fotografías inteligente con reconocimiento facial."
APP_MAINTAINER="Daniel Serrano Armenta <dani.eus79@gmil.com>" # REEMPLAZAR
APP_VENDOR="VisageVault Project"
INSTALL_PREFIX="/opt/$APP_NAME"
# La versión debe limpiarse de caracteres de tag como 'v'
CLEAN_VERSION=$(echo "$VERSION" | sed 's/^v//')

# Crear el directorio temporal de instalación
mkdir -p "$INSTALL_PREFIX"

# Mover el binario compilado al directorio de instalación
cp "$EXECUTABLE_PATH" "$INSTALL_PREFIX/visagevault-bin"

# 1. GENERAR PAQUETE .DEB
fpm -s dir -t deb \
    -n "$APP_NAME" \
    -v "$CLEAN_VERSION" \
    --iteration "1" \
    --description "$APP_DESCRIPTION" \
    --maintainer "$APP_MAINTAINER" \
    --vendor "$APP_VENDOR" \
    -p "$APP_NAME-$CLEAN_VERSION.deb" \
    --deb-priority optional \
    --deb-suggests 'ffmpeg' \
    --url 'https://github.com/danitxu79/visagevault' \
    -C "$INSTALL_PREFIX" \
    --prefix "/"

# 2. GENERAR PAQUETE .RPM
fpm -s dir -t rpm \
    -n "$APP_NAME" \
    -v "$CLEAN_VERSION" \
    --iteration "1" \
    --description "$APP_DESCRIPTION" \
    --maintainer "$APP_MAINTAINER" \tu-email@ejemplo.com
    --vendor "$APP_VENDOR" \
    -p "$APP_NAME-$CLEAN_VERSION.rpm" \
    --url 'https://github.com/danitxu79/visagevault' \
    -C "$INSTALL_PREFIX" \
    --prefix "/"

echo "--- ✅ Paquetes DEB y RPM creados. ---"
