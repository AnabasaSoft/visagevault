# drive_auth.py
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import sys
import threading

# Permisos: Solo lectura para ver fotos (más seguro y genera menos desconfianza)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class DriveAuthenticator:
    def __init__(self):
        self.creds = None
        # Ruta donde guardaremos la sesión del usuario para no pedirla siempre
        self.token_path = os.path.join(os.path.dirname(__file__), 'user_token.pickle')
        # Tu archivo maestro (que el usuario no toca)
        self.secrets_path = resource_path('client_secrets.json')

    def get_service(self):
        """Intenta loguear silenciosamente, o abre navegador si hace falta."""

        # 1. Cargar sesión guardada si existe
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)

        # 2. Si no hay credenciales válidas, hacemos el login visual
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    # Intenta refrescar el token sin abrir el navegador
                    self.creds.refresh(Request())
                except Exception:
                    self._start_browser_login()
            else:
                self._start_browser_login()

            # 3. Guardar la sesión para la próxima vez
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        # 4. Retornar el servicio listo para usar
        return build('drive', 'v3', credentials=self.creds)

    def _start_browser_login(self):
        """Lanza el flujo de 'Logueate con Google' en el navegador."""
        if not os.path.exists(self.secrets_path):
            raise FileNotFoundError("Falta el archivo de configuración interna (client_secrets.json).")

        flow = InstalledAppFlow.from_client_secrets_file(
            self.secrets_path, SCOPES)

        # CAMBIO CLAVE: Especificar success_message para asegurar que el usuario vea que acabó
        # y el servidor sepa que debe cerrarse.
        self.creds = flow.run_local_server(
            port=0,
            success_message='La autenticación se ha completado. Puedes cerrar esta ventana.'
        )


# --- FUNCIÓN AUXILIAR (Necesaria para encontrar client_secrets.json en el .exe) ---
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
