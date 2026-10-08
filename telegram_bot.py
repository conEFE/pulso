"""
Avisos por Telegram: cuando la Bandeja IA detecta tickets de prioridad alta, PULSO los envía a un chat.

Configuración (una vez):
  1. En Telegram, habla con @BotFather, crea un bot con /newbot y copia el token.
  2. Pega el token en PULSO (Canales → Telegram) y verifícalo.
  3. Abre tu bot en Telegram y envíale /start; PULSO detecta el chat automáticamente.

El token es un secreto: se guarda solo en este PC (%APPDATA%\\PULSO\\config.json), nunca en el repositorio.
"""
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{metodo}"
CARPETA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "PULSO")
ARCHIVO = os.path.join(CARPETA, "config.json")
MAX_POR_LOTE = 5


class ErrorTelegram(Exception):
    pass


# ---------------------------------------------------------------- configuración local
def cargar():
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            return json.load(f).get("telegram", {})
    except (OSError, ValueError):
        return {}


def guardar(conf):
    os.makedirs(CARPETA, exist_ok=True)
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            todo = json.load(f)
    except (OSError, ValueError):
        todo = {}
    todo["telegram"] = conf
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(todo, f, ensure_ascii=False, indent=2)


def configurado(conf):
    return bool(conf.get("token") and conf.get("chat_id"))


# ---------------------------------------------------------------- API de Telegram
def _llamar(token, metodo, datos=None, timeout=10):
    if not token or ":" not in token:
        raise ErrorTelegram("El token no tiene el formato correcto (números:letras).")
    url = API.format(token=urllib.parse.quote(token.strip(), safe=":"), metodo=metodo)
    cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=cuerpo), timeout=timeout) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise ErrorTelegram("Telegram rechazó el token. Revisa que esté completo.") from None
        if e.code == 400:
            raise ErrorTelegram("Telegram no encontró el chat. Envía /start a tu bot y vuelve a detectarlo.") from None
        raise ErrorTelegram(f"Telegram respondió con un error ({e.code}).") from None
    except urllib.error.URLError as e:
        raise ErrorTelegram(explicar_error_red(getattr(e, "reason", e))) from None
    except (TimeoutError, OSError) as e:
        raise ErrorTelegram(explicar_error_red(e)) from None
    if not resp.get("ok"):
        raise ErrorTelegram(resp.get("description", "Telegram respondió con un error."))
    return resp["result"]


def explicar_error_red(motivo):
    """Traduce el error de conexión a una causa concreta, para que el usuario sepa qué revisar."""
    t = str(motivo)
    if "CERTIFICATE_VERIFY_FAILED" in t or "SSL" in t:
        causa = ("La conexión segura con Telegram fue interceptada. Suele pasar en redes de empresa o de "
                 "universidad que inspeccionan el tráfico, o si la fecha y hora del PC están mal.")
    elif "getaddrinfo" in t or "11001" in t or "11004" in t:
        causa = "Este PC no encuentra los servidores de Telegram: no hay internet o la red bloquea Telegram."
    elif "timed out" in t or "10060" in t or isinstance(motivo, TimeoutError):
        causa = "Telegram no respondió a tiempo: la red o un firewall podría estar bloqueándolo."
    elif "10061" in t or "10013" in t or "refused" in t.lower():
        causa = "La red, un firewall o el antivirus rechazó la conexión con Telegram."
    else:
        causa = "No se pudo conectar con Telegram."
    return f"{causa} (Detalle técnico: {t[:120]})"


def verificar_token(token):
    """Devuelve el nombre de usuario del bot (sin @)."""
    return _llamar(token, "getMe")["username"]


def detectar_chat(token):
    """Busca el último chat que le escribió al bot. Devuelve (chat_id, nombre) o None."""
    for upd in reversed(_llamar(token, "getUpdates", {"limit": 20})):
        msg = upd.get("message") or upd.get("channel_post")
        if msg and msg.get("chat"):
            chat = msg["chat"]
            nombre = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
            return str(chat["id"]), nombre or str(chat["id"])
    return None


def enviar(token, chat_id, texto):
    _llamar(token, "sendMessage", {"chat_id": chat_id, "text": texto, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"})


# ---------------------------------------------------------------- mensajes
def mensaje_ticket(t):
    msg = t["mensaje"] if len(t["mensaje"]) <= 300 else t["mensaje"][:300] + "…"
    return (f"🔴 <b>Ticket crítico {html.escape(t['ticket'])}</b>\n"
            f"<b>Tema:</b> {html.escape(t['tema'])}\n"
            f"<b>Área:</b> {html.escape(t['area'])} · <b>Responder en:</b> {html.escape(t['sla'])}\n"
            f"<b>Canal:</b> {html.escape(t['canal'])}\n\n"
            f"<i>«{html.escape(msg)}»</i>")


def avisar_criticos(conf, tickets):
    """Envía los tickets de prioridad alta (como máximo MAX_POR_LOTE y un resumen del resto). Devuelve cuántos."""
    criticos = [t for t in tickets if t["prioridad"] == "Alta"]
    if not criticos or not configurado(conf):
        return 0
    for t in criticos[:MAX_POR_LOTE]:
        enviar(conf["token"], conf["chat_id"], mensaje_ticket(t))
    resto = len(criticos) - MAX_POR_LOTE
    if resto > 0:
        enviar(conf["token"], conf["chat_id"], f"… y {resto} tickets críticos más en la Bandeja IA de PULSO.")
    return len(criticos)


def mensaje_resumen(periodo, kpis, alertas):
    """kpis: [(nombre, valor, variación)]; alertas: [(título, detalle)]."""
    lineas = [f"📊 <b>PULSO · Resumen del mes</b> ({html.escape(periodo)})", ""]
    lineas += [f"<b>{html.escape(n)}:</b> {html.escape(v)}  <i>{html.escape(var)}</i>" for n, v, var in kpis]
    if alertas:
        lineas += ["", "<b>Requiere atención</b>"]
        lineas += [f"• {html.escape(t)}" for t, _ in alertas]
    return "\n".join(lineas)


def mensaje_vendedores(filas, en_riesgo, total, promedio):
    """filas: [(código, reseñas, % negativas, motivo, categoría)] de los vendedores en riesgo con más reclamos."""
    lineas = [f"⚠️ <b>{en_riesgo} vendedores en riesgo</b> (de {total} con 20+ reseñas)",
              f"Tienen más del doble de reseñas negativas que el promedio ({promedio}).", ""]
    if len(filas) < en_riesgo:
        lineas.insert(2, f"Los {len(filas)} con más reclamos:")
    for i, (cod, n, neg, motivo, cat) in enumerate(filas, start=1):
        lineas.append(f"{i}. <b>{html.escape(cod)}</b> · {html.escape(neg)} negativas de {n} · "
                      f"{html.escape(motivo)} · {html.escape(cat)}")
    lineas += ["", "Sugerencia: enviarles un plan de mejora desde el Seller Center."]
    return "\n".join(lineas)


def mensaje_por_vencer(t, minutos):
    msg = t["mensaje"] if len(t["mensaje"]) <= 200 else t["mensaje"][:200] + "…"
    cuando = (f"venció hace {abs(minutos)} min" if minutos < 0 else f"vence en {minutos} min")
    return (f"⏰ <b>Ticket urgente sin aprobar: {html.escape(t['ticket'])}</b>\n"
            f"{cuando} (a las {t['limite']:%H:%M})\n"
            f"<b>Tema:</b> {html.escape(t['tema'])} · <b>Área:</b> {html.escape(t['area'])}\n\n"
            f"<i>«{html.escape(msg)}»</i>")
