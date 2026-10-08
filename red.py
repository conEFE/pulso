"""
Conexiones HTTPS de PULSO (Telegram y actualizaciones desde GitHub).

En Windows usa WinHTTP, el sistema de red del propio sistema operativo: respeta el proxy configurado en Windows
(también el automático o por script, como en redes de empresa y universidad), se autentica en él con la sesión de
Windows y confía en los mismos certificados que el navegador. Si WinHTTP no está disponible o falla, usa urllib.
"""
import ctypes
import sys
import urllib.error
import urllib.parse
import urllib.request

AGENTE = "PULSO"


class ErrorRed(Exception):
    """Falla de conexión (no una respuesta HTTP con error: esas se devuelven con su código)."""


# ---------------------------------------------------------------- mensajes claros para cada causa
_CAUSAS_WINHTTP = {
    12007: "Este PC no encuentra el servidor: no hay internet o la red lo bloquea.",
    12002: "El servidor no respondió a tiempo: la red o un firewall podría estar bloqueándolo.",
    12029: "No se pudo abrir la conexión: la red, un firewall o el antivirus la rechazó.",
    12030: "La conexión se cortó: la red, un firewall o el antivirus la interrumpió.",
    12175: "La conexión segura falló: el certificado no es de confianza en este PC o la fecha y hora están mal.",
    12045: "La conexión segura falló: el certificado no es de confianza en este PC.",
    12057: "La conexión segura falló: no se pudo comprobar el certificado.",
    12180: "No se pudo detectar automáticamente el proxy de la red.",
    12166: "El script de proxy de la red tiene un error.",
    12167: "No se pudo descargar el script de proxy de la red.",
}


def explicar(motivo):
    """Causa concreta + detalle técnico, para que el usuario sepa qué revisar."""
    t = str(motivo)
    if "CERTIFICATE_VERIFY_FAILED" in t or "SSL" in t:
        causa = ("La conexión segura fue interceptada. Suele pasar en redes de empresa o de universidad que "
                 "inspeccionan el tráfico, o si la fecha y hora del PC están mal.")
    elif "getaddrinfo" in t or "11001" in t or "11004" in t:
        causa = "Este PC no encuentra el servidor: no hay internet o la red lo bloquea."
    elif "timed out" in t or "10060" in t or isinstance(motivo, TimeoutError):
        causa = "El servidor no respondió a tiempo: la red o un firewall podría estar bloqueándolo."
    elif "10061" in t or "10013" in t or "refused" in t.lower():
        causa = "La red, un firewall o el antivirus rechazó la conexión."
    else:
        causa = "No se pudo conectar."
    return f"{causa} (Detalle técnico: {t[:120]})"


# ---------------------------------------------------------------- WinHTTP (Windows)
_winhttp = None
if sys.platform == "win32":
    try:
        from ctypes import wintypes

        _winhttp = ctypes.WinDLL("winhttp", use_last_error=True)
        _H = ctypes.c_void_p
        _f = _winhttp
        _f.WinHttpOpen.restype = _H
        _f.WinHttpOpen.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                   wintypes.DWORD]
        _f.WinHttpConnect.restype = _H
        _f.WinHttpConnect.argtypes = [_H, wintypes.LPCWSTR, ctypes.c_ushort, wintypes.DWORD]
        _f.WinHttpOpenRequest.restype = _H
        _f.WinHttpOpenRequest.argtypes = [_H, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                          wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD]
        _f.WinHttpSetTimeouts.argtypes = [_H, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        _f.WinHttpSetOption.argtypes = [_H, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        _f.WinHttpSendRequest.argtypes = [_H, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                          wintypes.DWORD, ctypes.c_size_t]
        _f.WinHttpReceiveResponse.argtypes = [_H, ctypes.c_void_p]
        _f.WinHttpQueryHeaders.argtypes = [_H, wintypes.DWORD, wintypes.LPCWSTR, ctypes.c_void_p,
                                           ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
        _f.WinHttpQueryAuthSchemes.argtypes = [_H, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                                               ctypes.POINTER(wintypes.DWORD)]
        _f.WinHttpSetCredentials.argtypes = [_H, wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                             ctypes.c_void_p]
        _f.WinHttpQueryDataAvailable.argtypes = [_H, ctypes.POINTER(wintypes.DWORD)]
        _f.WinHttpReadData.argtypes = [_H, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        _f.WinHttpCloseHandle.argtypes = [_H]
    except (OSError, AttributeError):
        _winhttp = None

_AUTOMATICO, _POR_DEFECTO = 4, 0           # WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY (Win 8.1+) / DEFAULT_PROXY
_SEGURO = 0x00800000                       # WINHTTP_FLAG_SECURE
_OPT_PROTOCOLOS, _OPT_AUTOLOGON = 84, 77   # WINHTTP_OPTION_SECURE_PROTOCOLS / AUTOLOGON_POLICY


def _error_winhttp(paso):
    codigo = ctypes.get_last_error()
    causa = _CAUSAS_WINHTTP.get(codigo, "No se pudo conectar.")
    return ErrorRed(f"{causa} (Detalle técnico: WinHTTP {codigo} en {paso})")


def _winhttp_peticion(url, datos, cabeceras, timeout, progreso, cancelado):
    from ctypes import wintypes

    f = _winhttp
    partes = urllib.parse.urlsplit(url)
    ruta = (partes.path or "/") + (f"?{partes.query}" if partes.query else "")
    sesion = f.WinHttpOpen(AGENTE, _AUTOMATICO, None, None, 0) or f.WinHttpOpen(AGENTE, _POR_DEFECTO, None, None, 0)
    if not sesion:
        raise _error_winhttp("WinHttpOpen")
    conexion = peticion_h = None
    try:
        for protocolos in (0x800 | 0x2000, 0x800):          # TLS 1.2 + 1.3; si el sistema no tiene 1.3, solo 1.2
            v = wintypes.DWORD(protocolos)
            if f.WinHttpSetOption(sesion, _OPT_PROTOCOLOS, ctypes.byref(v), 4):
                break
        ms = int(timeout * 1000)
        f.WinHttpSetTimeouts(sesion, ms, ms, ms, ms)
        conexion = f.WinHttpConnect(sesion, partes.hostname, partes.port or 443, 0)
        if not conexion:
            raise _error_winhttp("WinHttpConnect")
        peticion_h = f.WinHttpOpenRequest(conexion, "POST" if datos else "GET", ruta, None, None, None, _SEGURO)
        if not peticion_h:
            raise _error_winhttp("WinHttpOpenRequest")
        bajo = wintypes.DWORD(0)                             # WINHTTP_AUTOLOGON_SECURITY_LEVEL_LOW: proxy con sesión de Windows
        f.WinHttpSetOption(peticion_h, _OPT_AUTOLOGON, ctypes.byref(bajo), 4)
        cab = dict(cabeceras or {})
        if datos:
            cab.setdefault("Content-Type", "application/x-www-form-urlencoded")
        texto_cab = "".join(f"{k}: {v}\r\n" for k, v in cab.items())
        cuerpo = ctypes.create_string_buffer(datos, len(datos)) if datos else None

        for _ in range(2):                                    # un reintento si el proxy pide autenticación (407)
            ok = f.WinHttpSendRequest(peticion_h, texto_cab or None, len(texto_cab) if texto_cab else 0,
                                      cuerpo, len(datos or b""), len(datos or b""), 0)
            if not ok:
                raise _error_winhttp("WinHttpSendRequest")
            if not f.WinHttpReceiveResponse(peticion_h, None):
                raise _error_winhttp("WinHttpReceiveResponse")
            estado = wintypes.DWORD(0)
            largo = wintypes.DWORD(4)
            f.WinHttpQueryHeaders(peticion_h, 19 | 0x20000000, None, ctypes.byref(estado), ctypes.byref(largo), None)
            if estado.value != 407:
                break
            soportados, primero, destino = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
            if not f.WinHttpQueryAuthSchemes(peticion_h, ctypes.byref(soportados), ctypes.byref(primero),
                                             ctypes.byref(destino)):
                break
            esquema = next((s for s in (0x10, 0x2) if soportados.value & s), primero.value)   # Negotiate, NTLM
            f.WinHttpSetCredentials(peticion_h, 1, esquema, None, None, None)                  # credenciales de Windows

        trozos, leido = [], 0
        while True:
            if cancelado and cancelado():
                raise InterruptedError("Descarga cancelada.")
            disponible = wintypes.DWORD(0)
            if not f.WinHttpQueryDataAvailable(peticion_h, ctypes.byref(disponible)):
                raise _error_winhttp("WinHttpQueryDataAvailable")
            if disponible.value == 0:
                break
            buf = ctypes.create_string_buffer(disponible.value)
            n = wintypes.DWORD(0)
            if not f.WinHttpReadData(peticion_h, buf, disponible.value, ctypes.byref(n)):
                raise _error_winhttp("WinHttpReadData")
            trozos.append(buf.raw[:n.value])
            leido += n.value
            if progreso:
                progreso(leido)
        return estado.value, b"".join(trozos)
    finally:
        for h in (peticion_h, conexion, sesion):
            if h:
                f.WinHttpCloseHandle(h)


# ---------------------------------------------------------------- urllib (respaldo)
def _urllib_peticion(url, datos, cabeceras, timeout, progreso, cancelado):
    req = urllib.request.Request(url, data=datos, headers={"User-Agent": AGENTE, **(cabeceras or {})})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise ErrorRed(explicar(getattr(e, "reason", e))) from None
    except (TimeoutError, OSError) as e:
        raise ErrorRed(explicar(e)) from None
    trozos, leido = [], 0
    with r:
        while True:
            if cancelado and cancelado():
                raise InterruptedError("Descarga cancelada.")
            bloque = r.read(1 << 16)
            if not bloque:
                break
            trozos.append(bloque)
            leido += len(bloque)
            if progreso:
                progreso(leido)
        return r.status, b"".join(trozos)


def peticion(url, datos=None, cabeceras=None, timeout=15, progreso=None, cancelado=None):
    """GET (o POST si hay `datos`, en bytes). Devuelve (código HTTP, cuerpo en bytes); lanza ErrorRed si no conecta."""
    if _winhttp is not None:
        try:
            return _winhttp_peticion(url, datos, cabeceras, timeout, progreso, cancelado)
        except ErrorRed as error_windows:
            try:
                return _urllib_peticion(url, datos, cabeceras, timeout, progreso, cancelado)
            except ErrorRed:
                raise error_windows from None
    return _urllib_peticion(url, datos, cabeceras, timeout, progreso, cancelado)
