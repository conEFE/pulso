"""
Actualización automática de PULSO desde los Releases de GitHub.

- buscar(): consulta el último Release y lo devuelve si es más nuevo que la versión actual.
- descargar(): baja el instalador y verifica su huella SHA-256 contra la que publica GitHub.
- instalar(): lanza el instalador en modo silencioso; el instalador cierra y vuelve a abrir la app.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

import red

REPO = "conEFE/pulso"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
PAGINA = f"https://github.com/{REPO}/releases/latest"
CABECERAS = {"User-Agent": "PULSO-actualizador", "Accept": "application/vnd.github+json"}


def version_tupla(texto):
    return tuple(int(n) for n in re.findall(r"\d+", str(texto))[:3])


def es_instalado():
    """True si corre la versión instalada con el asistente (tiene desinstalador junto al .exe)."""
    return bool(getattr(sys, "frozen", False)) and os.path.exists(
        os.path.join(os.path.dirname(sys.executable), "unins000.exe"))


def buscar(version_actual, timeout=6):
    """Devuelve los datos del último Release si es más nuevo; None si no hay versión nueva."""
    codigo, contenido = red.peticion(API, cabeceras=CABECERAS, timeout=timeout)   # proxy y certificados de Windows
    if codigo != 200:
        raise red.ErrorRed(f"GitHub respondió con el código {codigo}.")
    rel = json.loads(contenido)
    nueva = rel.get("tag_name", "")
    if version_tupla(nueva) <= version_tupla(version_actual):
        return None
    instalador = next((a for a in rel.get("assets", [])
                       if a["name"].lower().startswith("pulso_setup") and a["name"].lower().endswith(".exe")), None)
    return {
        "version": nueva.lstrip("v"),
        "notas": rel.get("body") or "",
        "pagina": rel.get("html_url") or PAGINA,
        "instalador": None if instalador is None else {
            "nombre": instalador["name"],
            "url": instalador["browser_download_url"],
            "tamano": instalador["size"],
            "sha256": (instalador.get("digest") or "").removeprefix("sha256:").lower(),
        },
    }


def descargar(instalador, progreso=None, cancelado=lambda: False):
    """Descarga el instalador a la carpeta temporal y verifica tamaño y SHA-256. Devuelve la ruta."""
    url = instalador["url"]
    if not url.startswith(f"https://github.com/{REPO}/releases/download/"):
        raise ValueError("El instalador no proviene del repositorio oficial de PULSO.")
    destino = os.path.join(tempfile.gettempdir(), instalador["nombre"])
    total = instalador["tamano"]
    codigo, contenido = red.peticion(url, timeout=60, cancelado=cancelado,
                                     progreso=(lambda leido: progreso(leido, total)) if progreso else None)
    if codigo != 200:
        raise IOError(f"GitHub respondió con el código {codigo} al descargar.")
    if len(contenido) != total:
        raise IOError("La descarga quedó incompleta.")
    if instalador["sha256"] and hashlib.sha256(contenido).hexdigest() != instalador["sha256"]:
        raise IOError("La huella SHA-256 no coincide con la publicada en GitHub: el archivo no se instalará.")
    with open(destino, "wb") as f:
        f.write(contenido)
    return destino


def instalar(ruta):
    """Lanza el instalador en silencio. Quien llama debe cerrar la app justo después."""
    subprocess.Popen([ruta, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RELAUNCH"],
                     close_fds=True)
