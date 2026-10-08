"""
PULSO · Centro de Operaciones Digitales para e-commerce.

Espacio de trabajo de demostración: Olist Store (marketplace, Brasil), con datos reales del
Brazilian E-Commerce Public Dataset by Olist (Kaggle).

Módulos:
  Inicio      panel diario: KPIs del último mes, alertas y acciones rápidas
  Analítica   ventas, logística y pagos con insights y acción recomendada
  Bandeja IA  clasificación automática de reseñas y reclamos, tickets y respuestas
  Canales     integraciones (WhatsApp, email, CRM, Seller Center...) y reglas de automatización
"""
import datetime as dt
import os
import random
import sys
import threading
import time
import unicodedata
import webbrowser

import customtkinter as ctk
import joblib
import matplotlib
import matplotlib.colors
import pandas as pd
from tkinter import filedialog, messagebox, ttk

import actualizador
import telegram_bot
from casos_prueba import ESCENARIOS, SUITE, generar

# Clases del modelo guardado: se importan explícitamente para que PyInstaller las incluya en el .exe
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
from sklearn.linear_model import LogisticRegression  # noqa: F401
from sklearn.pipeline import Pipeline  # noqa: F401

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

APP_NOMBRE = "PULSO"
VERSION = "1.6.0"
ESPACIO = "Olist Store"

# ---------------------------------------------------------------- identidad visual
TINTA = "#0E2235"        # azul tinta: barra lateral, encabezados, datos principales
TINTA_2 = "#1B3550"      # tinta clara: hover / ítem activo
PAPEL = "#F3F0E8"        # fondo cálido tipo papel
BLANCO = "#FFFFFF"
LINEA = "#DCD6C8"        # líneas finas
TEXTO = "#1A2530"
TEXTO_2 = "#6B675E"      # texto secundario cálido
COBRE = "#C2502F"        # acento: lo que exige atención
OCRE = "#C98A1B"         # advertencia / prioridad media
PETROLEO = "#2E6B66"     # positivo / activo
PIZARRA = "#8A97A5"      # datos de contexto
CAMPO = "#F7F5EF"        # fondo de campos de texto
TINTE_ALTA, TINTE_MEDIA, TINTE_BAJA = "#F5E4DD", "#F6EDD9", "#FFFFFF"

DISPLAY = "Bahnschrift"
DISPLAY_SB = "Bahnschrift SemiBold"
CUERPO = "Segoe UI"
CUERPO_SB = "Segoe UI Semibold"

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                "noviembre", "diciembre"]

matplotlib.rcParams.update({
    "font.family": ["Franklin Gothic Book", "Segoe UI", "DejaVu Sans"], "font.size": 9,
    "text.color": TEXTO, "axes.labelcolor": TEXTO_2, "xtick.color": TEXTO_2, "ytick.color": TEXTO_2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.edgecolor": LINEA, "axes.titlesize": 12, "axes.titlelocation": "left",
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#ECE8DE", "grid.linewidth": 0.8,
    "axes.axisbelow": True, "xtick.major.size": 0, "ytick.major.size": 0,
})


def recurso(ruta):
    """Ruta a un archivo incluido, tanto en desarrollo como dentro del .exe (PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, ruta)


def num(v, dec=0):
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, dec=1):
    return f"{num(v * 100, dec)}%"


def millones(v):
    return f"R$ {num(v / 1e6, 2)} M" if v >= 1e6 else f"R$ {num(v / 1e3, 0)} mil"


def sin_tildes(texto):
    t = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def mes_txt(periodo):
    return f"{MESES[periodo.month - 1]}-{str(periodo.year)[2:]}"


def plazo(sla):
    """'2 h' → timedelta de 2 horas."""
    return dt.timedelta(hours=int(str(sla).split()[0]))


def duracion(minutos):
    m = int(round(minutos))
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d} min"


def variacion(actual, anterior, puntos=False):
    """Texto y color de una variación respecto del período anterior."""
    if anterior in (0, None) or pd.isna(anterior):
        return "", TEXTO_2
    d = (actual - anterior) * 100 if puntos else (actual / anterior - 1) * 100
    signo = "▲" if d > 0 else ("▼" if d < 0 else "■")
    unidad = " pp" if puntos else "%"
    return f"{signo} {num(abs(d), 1)}{unidad} vs. mes anterior", d


# ---------------------------------------------------------------- canales e integraciones
CANALES = [
    {"id": "whatsapp", "nombre": "WhatsApp Business", "publico": "Clientes", "activo": True,
     "hace": "Avisa despachos y atrasos, y atiende los reclamos de prioridad alta en menos de 2 horas."},
    {"id": "email", "nombre": "Email", "publico": "Clientes", "activo": True,
     "hace": "Confirma compras, recuerda el pago del boleto, envía encuestas y responde casos de prioridad media."},
    {"id": "crm", "nombre": "CRM", "publico": "Clientes", "activo": True,
     "hace": "Recibe cada ticket que crea la bandeja IA y guarda el historial del cliente para fidelizar."},
    {"id": "seller", "nombre": "Seller Center", "publico": "Proveedores", "activo": True,
     "hace": "Alerta a cada vendedor por atrasos y reclamos de calidad, con su ranking de cumplimiento."},
    {"id": "erp", "nombre": "ERP / API de pedidos", "publico": "Proveedores", "activo": False,
     "hace": "Sincroniza stock, precios y estado del pedido con los vendedores sin digitación manual."},
    {"id": "redes", "nombre": "Redes sociales", "publico": "Clientes", "activo": False,
     "hace": "Publica campañas en fechas peak y difunde las reseñas positivas que marca la IA."},
    {"id": "teams", "nombre": "Microsoft Teams", "publico": "Equipo interno", "activo": True,
     "hace": "Avisa a Logística, Calidad y Finanzas cuando entra un ticket crítico de su área."},
    # Integración real (no simulada): se configura con el token de un bot de Telegram
    {"id": "telegram", "nombre": "Telegram", "publico": "Equipo interno", "activo": False,
     "hace": "Envía al celular un aviso en segundos cada vez que la Bandeja IA detecta un ticket crítico."},
]

REGLAS = [
    ("Reseña negativa crítica (no recibido, defecto, reembolso)", "Responder y abrir ticket", "whatsapp", "2 h"),
    ("Reseña negativa no crítica", "Responder y abrir ticket", "email", "24 h"),
    ("Ticket de prioridad alta creado", "Alertar al área responsable", "teams", "inmediato"),
    ("Ticket de prioridad alta creado", "Avisar al celular del equipo", "telegram", "inmediato"),
    ("Reseña positiva", "Agradecer, enviar cupón e invitar a compartir", "redes", "72 h"),
    ("Pedido supera la fecha prometida", "Aviso proactivo al cliente", "whatsapp", "mismo día"),
    ("Boleto emitido sin pagar por 48 h", "Recordatorio de pago", "email", "48 h"),
    ("Vendedor con más de 10% de atrasos en el mes", "Alerta y plan de mejora", "seller", "semanal"),
    ("Pedido nuevo", "Sincronizar con el vendedor", "erp", "inmediato"),
]


# ---------------------------------------------------------------- reglas del proceso automatizado
# (tema, palabras clave en portugués sin tildes, área responsable)
TEMAS = [
    ("No recibido", ["nao recebi", "nao chegou", "ainda nao", "nao foi entregue", "aguardando", "nao veio",
                     "nao recebido", "nada do", "nunca chegou", "nao chegar", "nao recebemos"], "Logística"),
    ("Reembolso / cancelación", ["devol", "reembols", "estorno", "cancel", "dinheiro de volta"], "Finanzas"),
    ("Producto defectuoso", ["defeito", "quebrad", "danific", "nao funciona", "estragad", "rasgad", "amassad"], "Calidad"),
    ("Producto incorrecto o incompleto", ["errad", "diferente", "faltando", "falta", "incomplet", "veio so",
                                          "veio apenas", "outro produto", "somente"], "Calidad"),
    ("Retraso en la entrega", ["atras", "demor", "prazo", "lent"], "Logística"),
    ("Atención del vendedor", ["atendimento", "vendedor", "resposta", "contato", "loja", "sac"], "Atención al cliente"),
    ("Calidad del producto", ["qualidade", "material", "fraco", "ruim", "pessim", "horrivel"], "Calidad"),
]
TEMAS_CRITICOS = {"No recibido", "Reembolso / cancelación", "Producto defectuoso"}
TEMAS_ENTREGA = {"No recibido", "Retraso en la entrega"}
TEMAS_CALIDAD = {"Producto defectuoso", "Producto incorrecto o incompleto", "Calidad del producto"}

RESPUESTAS = {
    "No recibido": "Hola, lamentamos que tu pedido aún no haya llegado. Abrimos el ticket {ticket} con el área de "
                   "Logística y te escribiremos {via} con el estado de tu envío en menos de {sla}.",
    "Reembolso / cancelación": "Hola, recibimos tu solicitud. El ticket {ticket} ya está en el área de Finanzas; "
                               "te contactaremos {via} para confirmar el reembolso o la cancelación en menos de {sla}.",
    "Producto defectuoso": "Hola, sentimos mucho que el producto haya llegado con fallas. Creamos el ticket {ticket} "
                           "y coordinaremos el cambio sin costo. Un ejecutivo te escribirá {via} en menos de {sla}.",
    "Producto incorrecto o incompleto": "Hola, gracias por avisarnos. Registramos el ticket {ticket} y notificamos al "
                                        "vendedor para enviar lo que falta o corregir el producto. Te informaremos {via}.",
    "Retraso en la entrega": "Hola, te pedimos disculpas por la demora. Con el ticket {ticket} priorizamos tu envío "
                             "con la transportadora y te enviaremos el seguimiento actualizado {via}.",
    "Atención del vendedor": "Hola, lamentamos tu experiencia. Escalamos el caso (ticket {ticket}) al equipo de "
                             "Atención al Cliente, que te contactará {via} en menos de {sla}.",
    "Calidad del producto": "Hola, gracias por tu comentario. Registramos el ticket {ticket} y compartimos tu "
                            "evaluación con el vendedor para mejorar la calidad. Si deseas un cambio, respóndenos {via}.",
    "General": "Hola, gracias por escribirnos. Registramos tu comentario (ticket {ticket}) y un ejecutivo lo revisará "
               "en menos de {sla}.",
    "Positivo": "¡Muchas gracias por tu comentario! Nos alegra que tu compra haya sido una buena experiencia. "
                "Te enviamos un cupón de 10% para tu próxima compra.",
}


# La misma respuesta en portugués: es la que realmente recibe el cliente en Brasil
RESPUESTAS_PT = {
    "No recibido": "Olá! Lamentamos que seu pedido ainda não tenha chegado. Abrimos o chamado {ticket} com a "
                   "Logística e vamos te escrever {via} com o status da entrega em menos de {sla}.",
    "Reembolso / cancelación": "Olá! Recebemos sua solicitação. O chamado {ticket} já está com o Financeiro; vamos "
                               "entrar em contato {via} para confirmar o reembolso ou o cancelamento em menos de {sla}.",
    "Producto defectuoso": "Olá! Sentimos muito que o produto tenha chegado com defeito. Criamos o chamado {ticket} e "
                           "vamos coordenar a troca sem custo. Um atendente vai te escrever {via} em menos de {sla}.",
    "Producto incorrecto o incompleto": "Olá! Obrigado por avisar. Registramos o chamado {ticket} e notificamos o "
                                        "vendedor para enviar o que falta ou corrigir o produto. Vamos te informar {via}.",
    "Retraso en la entrega": "Olá! Pedimos desculpas pela demora. Com o chamado {ticket} priorizamos seu envio com a "
                             "transportadora e enviaremos o rastreamento atualizado {via}.",
    "Atención del vendedor": "Olá! Lamentamos sua experiência. Encaminhamos o caso (chamado {ticket}) para a equipe de "
                             "Atendimento, que vai entrar em contato {via} em menos de {sla}.",
    "Calidad del producto": "Olá! Obrigado pelo comentário. Registramos o chamado {ticket} e compartilhamos sua "
                            "avaliação com o vendedor para melhorar a qualidade. Se quiser uma troca, responda {via}.",
    "General": "Olá! Obrigado por escrever. Registramos seu comentário (chamado {ticket}) e um atendente vai analisá-lo "
               "em menos de {sla}.",
    "Positivo": "Muito obrigado pelo seu comentário! Ficamos felizes que sua compra tenha sido uma boa experiência. "
                "Enviamos um cupom de 10% para sua próxima compra.",
}


def detectar_tema(texto):
    t = sin_tildes(texto)
    for tema, claves, area in TEMAS:
        if any(c in t for c in claves):
            return tema, area
    return "General", "Atención al cliente"


def decidir(sentimiento, tema, activos):
    """Regla de negocio: prioridad, canal de respuesta y plazo según los canales activos."""
    wa, mail = activos.get("whatsapp"), activos.get("email")
    escrito = "Email + ticket CRM" if mail else "Ticket CRM"
    if sentimiento == "Negativo":
        if tema in TEMAS_CRITICOS:
            return "Alta", ("WhatsApp Business" if wa else escrito), "2 h"
        return "Media", escrito, "24 h"
    if sentimiento == "Neutro":
        return ("Media", escrito, "24 h") if tema != "General" else ("Baja", "Email (encuesta)" if mail else
                                                                    "Ticket CRM", "72 h")
    return "Baja", ("Redes sociales + cupón" if activos.get("redes") else ("Email + cupón" if mail else
                                                                         "Ticket CRM")), "72 h"


def evaluar_casos(datos, casos):
    """Pasa cada caso por el sistema real (modelo + reglas) y lo compara con su resultado esperado."""
    if not casos:
        return pd.DataFrame()
    textos = [c["mensaje"] for c in casos]
    proba = datos.modelo.predict_proba(textos)
    sents = [datos.modelo.classes_[p.argmax()] for p in proba]
    palabras = datos.explicar(textos, sents)
    filas = []
    for c, p, s, pal in zip(casos, proba, sents, palabras):
        tema = "Elogio / comentario positivo" if s == "Positivo" else detectar_tema(c["mensaje"])[0]
        filas.append({**c, "sent_ia": s, "confianza": p.max(), "tema_ia": tema, "palabras": ", ".join(pal),
                      "ok_sent": s == c["sentimiento"], "ok_tema": tema == c["tema"]})
    df = pd.DataFrame(filas)
    df["ok"] = df.ok_sent & df.ok_tema
    return df


# ---------------------------------------------------------------- datos
class Datos:
    def __init__(self):
        self.ventas = pd.read_csv(recurso("data/ventas.csv.gz"), parse_dates=["fecha"])
        self.resenas = pd.read_csv(recurso("data/resenas.csv.gz"))
        ia = joblib.load(recurso("data/modelo_ia.joblib"))
        self.modelo, self.precision = ia["modelo"], ia["accuracy"]
        self.n_train, self.n_test = ia["n_train"], ia["n_test"]
        self.etiquetas, self.matriz, self.reporte = ia["etiquetas"], ia["matriz"], ia["reporte"]
        self.ventas["mes"] = self.ventas.fecha.dt.to_period("M")
        self.ventas["anio"] = self.ventas.fecha.dt.year
        self.corte = self.ventas.fecha.max()
        self._nombres = self.modelo.named_steps["tfidf"].get_feature_names_out()
        self._evidencia()
        self._voz()

    def explicar(self, textos, clases, top=4):
        """Palabras que más empujaron al modelo hacia la clase elegida (peso TF-IDF × coeficiente)."""
        tfidf, clf = self.modelo.named_steps["tfidf"], self.modelo.named_steps["clf"]
        X = tfidf.transform(textos)
        k_de = {c: i for i, c in enumerate(clf.classes_)}
        salida = []
        for i, c in enumerate(clases):
            fila = X.getrow(i)
            aporte = fila.data * clf.coef_[k_de[c], fila.indices]
            elegidas = []
            for j in aporte.argsort()[::-1]:
                if aporte[j] <= 0 or len(elegidas) == top:
                    break
                t = self._nombres[fila.indices[j]]
                if not any(t in e or e in t for e in elegidas):   # evita "chegou" junto a "nao chegou"
                    elegidas.append(t)
            salida.append(elegidas)
        return salida

    def _voz(self):
        """Voz del cliente: todas las reseñas con texto clasificadas por la IA, por mes, tema y vendedor."""
        voz = pd.read_csv(recurso("data/voz_cliente.csv.gz"), parse_dates=["fecha"])
        voz["mes"] = voz.fecha.dt.to_period("M")
        voz = voz[(voz.mes >= pd.Period("2017-01", "M")) & (voz.mes <= pd.Period("2018-08", "M"))].copy()
        voz["tema"] = voz.texto.map(lambda t: detectar_tema(t)[0])
        voz["negativo"] = voz.sent_ia == "Negativo"
        self.voz = voz
        neg = voz[voz.negativo]
        # tema en alza: participación en los reclamos de los últimos 3 meses vs. los 3 anteriores
        fin = voz.mes.max()
        rec = neg[neg.mes > fin - 3].tema.value_counts(normalize=True)
        ant = neg[(neg.mes <= fin - 3) & (neg.mes > fin - 6)].tema.value_counts(normalize=True)
        cambio = (rec - ant).drop("General", errors="ignore").dropna().sort_values(ascending=False)
        self.tema_alza = (cambio.index[0], ant[cambio.index[0]], rec[cambio.index[0]]) if len(cambio) else None
        # ranking de vendedores con al menos 20 reseñas escritas
        g = voz.dropna(subset=["vendedor"]).groupby("vendedor")
        rk = g.agg(resenas=("negativo", "size"), pct_neg=("negativo", "mean"), nota=("nota", "mean"),
                   categoria=("categoria", lambda s: s.mode().iat[0] if s.notna().any() else "—"))
        rk["tema"] = neg.dropna(subset=["vendedor"]).groupby("vendedor").tema.agg(
            lambda s: (s[s != "General"].mode().iat[0] if (s != "General").any() else "General"))
        rk = rk[rk.resenas >= 20].copy()
        prom = voz.negativo.mean()
        rk["estado"] = pd.cut(rk.pct_neg, [-1, prom * 1.5, prom * 2, 2], labels=["Normal", "Observación", "En riesgo"])
        self.ranking = rk.sort_values("pct_neg", ascending=False)
        self.pct_neg_prom = prom

    def _evidencia(self):
        """Indicadores que justifican cada canal."""
        v = self.ventas
        neg = self.resenas[self.resenas.sentimiento == "Negativo"]
        temas = neg.texto.map(lambda t: detectar_tema(t)[0])
        compras = v.groupby("cliente").size()
        mensual = v.groupby("mes").valor.sum()
        self.ev = {
            "pct_neg_entrega": temas.isin(TEMAS_ENTREGA).mean(),
            "pct_neg_calidad": temas.isin(TEMAS_CALIDAD).mean(),
            "nota_atraso": v[v.atrasado == 1].nota.mean(),
            "nota_ok": v[v.atrasado == 0].nota.mean(),
            "pct_atraso": v.atrasado.mean(),
            "pct_boleto": (v.pago == "Boleto bancario").mean(),
            "pct_recompra": (compras > 1).mean(),
            "n_vendedores": v.vendedor.nunique(),
            "n_clientes": v.cliente.nunique(),
            "pedidos_mes": v.groupby("mes").size().mean(),
            "mes_peak": mensual.idxmax(),
        }
        ev = self.ev
        self.por_que = {
            "whatsapp": f"{pct(ev['pct_neg_entrega'], 0)} de los reclamos negativos son por la entrega; con atraso la "
                        f"nota cae de {num(ev['nota_ok'], 1)} a {num(ev['nota_atraso'], 1)}.",
            "email": f"{pct(ev['pct_boleto'], 0)} de los pedidos se paga con boleto, un pago diferido que hay que "
                     "recordar.",
            "crm": f"Solo {pct(ev['pct_recompra'])} de {num(ev['n_clientes'])} clientes vuelve a comprar.",
            "seller": f"{num(ev['n_vendedores'])} vendedores despachan; {pct(ev['pct_neg_calidad'], 0)} de los reclamos "
                      "negativos son de calidad.",
            "erp": f"Unos {num(ev['pedidos_mes'])} pedidos al mes pasan del marketplace al vendedor.",
            "redes": f"El peak de ventas fue {mes_txt(ev['mes_peak'])} (Black Friday).",
            "teams": f"{pct(ev['pct_atraso'])} de los pedidos se atrasa y requiere coordinar a varias áreas.",
            "telegram": f"{pct(ev['pct_neg_entrega'], 0)} de los reclamos negativos son por la entrega y deben "
                        "responderse en 2 horas, aunque nadie esté mirando la bandeja.",
        }


# ---------------------------------------------------------------- componentes de interfaz
def panel(padre, **kw):
    """Bloque de contenido del lienzo: sin marco; se separa por espacio y alineación (estilo reporte)."""
    return ctk.CTkFrame(padre, fg_color="transparent", corner_radius=0, **kw)


def linea(padre, **pack):
    ctk.CTkFrame(padre, height=1, fg_color=LINEA, corner_radius=0).pack(fill="x", **pack)


def rotulo(padre, texto, color=TEXTO_2, size=10):
    """Etiqueta corta en mayúsculas."""
    return ctk.CTkLabel(padre, text=texto.upper(), font=(CUERPO_SB, size), text_color=color, anchor="w")


def titulo_panel(p, texto, nota=None):
    """Título de un visual: nombre en tinta y una nota breve en gris debajo, como en un reporte."""
    fila = ctk.CTkFrame(p, fg_color="transparent")
    fila.pack(fill="x", padx=4, pady=(14, 6))
    ctk.CTkLabel(fila, text=texto, font=(DISPLAY_SB, 15), text_color=TINTA, anchor="w").pack(side="left")
    if nota:
        ctk.CTkLabel(fila, text=nota, font=(CUERPO, 11), text_color=TEXTO_2).pack(side="left", padx=(10, 0),
                                                                                   pady=(3, 0))
    return fila


def separador(padre, padx=36, pady=(14, 4)):
    """Línea fina que separa filas de visuales en el lienzo."""
    ctk.CTkFrame(padre, height=1, fg_color="#ECE8DE", corner_radius=0).pack(fill="x", padx=padx, pady=pady)


def encabezado(padre, titulo, contexto=None):
    """Encabezado del lienzo: contexto pequeño arriba y título; devuelve un contenedor a la derecha."""
    caja = ctk.CTkFrame(padre, fg_color="transparent")
    caja.pack(fill="x", padx=36, pady=(26, 10))
    acciones = ctk.CTkFrame(caja, fg_color="transparent", width=1, height=1)
    acciones.pack(side="right", anchor="s")
    textos = ctk.CTkFrame(caja, fg_color="transparent")
    textos.pack(side="left", anchor="w")
    ctk.CTkLabel(textos, text=contexto or ESPACIO, font=(CUERPO, 11), text_color=TEXTO_2, anchor="w").pack(fill="x")
    ctk.CTkLabel(textos, text=titulo, font=(DISPLAY_SB, 26), text_color=TINTA, anchor="w").pack(fill="x")
    return acciones


class FranjaKPI(ctk.CTkFrame):
    """Banda de indicadores: números grandes separados por líneas verticales finas, sin marco."""

    def __init__(self, padre, items):
        super().__init__(padre, fg_color="transparent", corner_radius=0)
        self.valores, self.notas = {}, {}
        for i, (clave, etiqueta, color) in enumerate(items):
            if i:
                ctk.CTkFrame(self, width=1, height=1, fg_color="#E4DFD3", corner_radius=0).grid(
                    row=0, column=2 * i - 1, sticky="ns", pady=6)
            celda = ctk.CTkFrame(self, fg_color="transparent")
            celda.grid(row=0, column=2 * i, sticky="nsew", padx=(4 if i == 0 else 18, 10), pady=6)
            self.grid_columnconfigure(2 * i, weight=1, uniform="kpi")
            ctk.CTkLabel(celda, text=etiqueta, font=(CUERPO, 12), text_color=TEXTO_2, anchor="w").pack(fill="x")
            self.valores[clave] = ctk.CTkLabel(celda, text="—", font=(DISPLAY_SB, 30), text_color=color, anchor="w")
            self.valores[clave].pack(fill="x")
            self.notas[clave] = ctk.CTkLabel(celda, text="", font=(CUERPO, 11), text_color=TEXTO_2, anchor="w")
            self.notas[clave].pack(fill="x")

    def set(self, clave, valor, nota=""):
        self.valores[clave].configure(text=valor)
        self.notas[clave].configure(text=nota)


def boton(padre, texto, comando, principal=True, **kw):
    kw.setdefault("height", 34)
    if principal:
        return ctk.CTkButton(padre, text=texto, command=comando, corner_radius=3, fg_color=TINTA,
                             hover_color=TINTA_2, font=(CUERPO_SB, 12), **kw)
    return ctk.CTkButton(padre, text=texto, command=comando, corner_radius=3, fg_color="transparent",
                         hover_color="#E9E4D8", border_width=1, border_color=TINTA, text_color=TINTA,
                         font=(CUERPO_SB, 12), **kw)


def selector(padre, valores, comando=None, ancho=150):
    """Segmentador tipo Power BI: píldora clara con flecha."""
    return ctk.CTkOptionMenu(padre, values=valores, command=comando, width=ancho, corner_radius=16, height=32,
                             fg_color="#F1EEE6", button_color="#F1EEE6", button_hover_color="#E6E0D2",
                             text_color=TEXTO, dropdown_fg_color=BLANCO, dropdown_text_color=TEXTO,
                             dropdown_hover_color="#EFEBE1", font=(CUERPO, 12), dropdown_font=(CUERPO, 12))


def pastilla(padre, texto, color, relleno=True):
    return ctk.CTkLabel(padre, text=texto, font=(CUERPO_SB, 10), corner_radius=3, height=22,
                        fg_color=color if relleno else "transparent", text_color="white" if relleno else color)


def estilo_tablas():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Treeview", font=(CUERPO, 10), rowheight=32, background=BLANCO, fieldbackground=BLANCO,
                foreground=TEXTO, borderwidth=0, relief="flat")
    s.configure("Treeview.Heading", font=(CUERPO_SB, 10), background="#EFEBE1", foreground=TEXTO,
                relief="flat", padding=(8, 8), borderwidth=0)
    s.map("Treeview.Heading", background=[("active", "#E6E0D2")])
    s.map("Treeview", background=[("selected", "#D7E0EA")], foreground=[("selected", TINTA)])
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.configure("Vertical.TScrollbar", background="#E6E0D2", troughcolor=BLANCO, borderwidth=0, arrowsize=12)


def estilo_ejes(ax, titulo, subtitulo=None):
    ax.set_title(titulo, fontsize=12.5, color=TINTA, loc="left", pad=22 if subtitulo else 12)
    if subtitulo:
        ax.text(0, 1.035, subtitulo, transform=ax.transAxes, fontsize=8.5, color=TEXTO_2, va="bottom")


def sparkline(padre, serie, color):
    fig = Figure(figsize=(2.4, 0.55), dpi=100, facecolor=BLANCO)
    ax = fig.add_axes([0, 0.05, 1, 0.9])
    ax.plot(range(len(serie)), serie, color=color, lw=1.8)
    ax.fill_between(range(len(serie)), serie, min(serie), color=color, alpha=0.08)
    ax.scatter([len(serie) - 1], [serie[-1]], color=color, s=14, zorder=3)
    ax.axis("off")
    c = FigureCanvasTkAgg(fig, master=padre)
    c.draw()
    return c.get_tk_widget()


# ---------------------------------------------------------------- Inicio
class PaginaInicio(ctk.CTkScrollableFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color=BLANCO, corner_radius=10)
        self.app = app
        d = app.datos
        v = d.ventas
        hora = dt.datetime.now().hour
        saludo = "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 20 else "Buenas noches")
        ultimo = v.mes.max()
        if (v[v.mes == ultimo].fecha.dt.day.max() or 0) < 25:   # mes incompleto: usar el anterior
            ultimo = ultimo - 1
        self.ultimo, previo = ultimo, ultimo - 1
        acciones = encabezado(self, "Resumen del mes",
                              f"{saludo}  ·  {MESES_LARGOS[ultimo.month - 1].capitalize()} {ultimo.year} frente a "
                              f"{MESES_LARGOS[previo.month - 1]}")
        boton(acciones, "Exportar informe", lambda: app.ir("analisis", exportar=True), principal=False,
              width=150).pack(side="right", padx=(8, 0))
        boton(acciones, "Procesar bandeja", lambda: app.ir("ia", procesar=True), width=150).pack(side="right")
        boton(acciones, "Resumen a Telegram", self.enviar_resumen, principal=False, width=170).pack(
            side="right", padx=(0, 8))
        self.lbl_tg = ctk.CTkLabel(acciones, text="", font=(CUERPO_SB, 11), text_color=TEXTO_2)
        self.lbl_tg.pack(side="right", padx=(0, 12))

        # Banda de KPIs del último mes
        mensual = v.groupby("mes").agg(ventas=("valor", "sum"), pedidos=("valor", "size"), nota=("nota", "mean"),
                                       atraso=("atrasado", "mean"))
        mensual = mensual[mensual.index <= ultimo]
        a, b = mensual.loc[ultimo], mensual.loc[previo]
        hist = mensual.tail(12)
        kpi = FranjaKPI(self, [("ventas", "Ventas", TINTA), ("pedidos", "Pedidos", TINTA),
                               ("nota", "Nota de clientes", PETROLEO), ("atraso", "Entregas atrasadas", COBRE)])
        kpi.pack(fill="x", padx=36, pady=(10, 0))
        self.periodo = f"{MESES_LARGOS[ultimo.month - 1]} {ultimo.year}"
        self.kpis_resumen = []
        nombres = {"ventas": "Ventas", "pedidos": "Pedidos", "nota": "Nota de clientes", "atraso": "Atrasos"}
        for clave, valor, (txt, delta), menos_es_mejor in [
            ("ventas", millones(a.ventas), variacion(a.ventas, b.ventas), False),
            ("pedidos", num(a.pedidos), variacion(a.pedidos, b.pedidos), False),
            ("nota", num(a.nota, 2), variacion(a.nota, b.nota), False),
            ("atraso", pct(a.atraso), variacion(a.atraso, b.atraso, puntos=True), True),
        ]:
            bueno = (delta < 0) if menos_es_mejor else (delta > 0)
            kpi.set(clave, valor, txt.replace("mes anterior", MESES_LARGOS[previo.month - 1]))
            self.kpis_resumen.append((nombres[clave], valor, txt.replace("mes anterior", MESES_LARGOS[previo.month - 1])))
            kpi.notas[clave].configure(text_color=PETROLEO if bueno else COBRE, font=(CUERPO_SB, 11))
        separador(self, pady=(18, 0))

        # Fila 1: ventas de los últimos 12 meses + categorías líderes
        fila1 = ctk.CTkFrame(self, fg_color="transparent")
        fila1.pack(fill="x", padx=32)
        fila1.grid_columnconfigure(0, weight=3, uniform="f1")
        fila1.grid_columnconfigure(1, weight=2, uniform="f1")
        p1 = panel(fila1)
        p1.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        titulo_panel(p1, "Ventas mensuales", "miles de R$ · últimos 12 meses")
        fig = Figure(figsize=(7.2, 2.6), dpi=100, facecolor=BLANCO)
        fig.subplots_adjust(left=0.06, right=0.99, top=0.88, bottom=0.12)
        ax = fig.add_subplot(111)
        valores = hist.ventas.values / 1e3
        ip = valores.argmax()
        ax.bar(range(len(valores)), valores, width=0.66, color=[COBRE if i == ip else TINTA for i in range(len(valores))])
        ax.set_xticks(range(len(valores)), [mes_txt(p) for p in hist.index], fontsize=8)
        ax.annotate(f"{mes_txt(hist.index[ip])} · {num(valores[ip])}", (ip, valores[ip]), xytext=(0, 5),
                    textcoords="offset points", ha="center", fontsize=8, color=COBRE)
        ax.set_ylim(0, valores.max() * 1.18)
        ax.tick_params(axis="y", labelsize=8)
        FigureCanvasTkAgg(fig, master=p1).get_tk_widget().pack(fill="x", padx=4)

        p2 = panel(fila1)
        p2.grid(row=0, column=1, sticky="nsew")
        anio = v[(v.mes > ultimo - 12) & (v.mes <= ultimo)]
        cats = (anio.groupby("categoria").valor.sum() / anio.valor.sum()).nlargest(6).sort_values()
        titulo_panel(p2, "Categorías líderes", "participación en ventas · 12 meses")
        fig2 = Figure(figsize=(4.8, 2.6), dpi=100, facecolor=BLANCO)
        fig2.subplots_adjust(left=0.36, right=0.9, top=0.95, bottom=0.05)
        ax2 = fig2.add_subplot(111)
        ax2.barh(cats.index, cats.values * 100, height=0.56, color=[PIZARRA] * (len(cats) - 1) + [TINTA])
        for i, val in enumerate(cats.values):
            ax2.text(val * 100, i, f"  {pct(val)}", va="center", fontsize=8.5, color=TEXTO)
        ax2.set_xlim(0, cats.max() * 100 * 1.25)
        ax2.grid(False)
        ax2.set_xticks([])
        ax2.spines["bottom"].set_visible(False)
        ax2.tick_params(axis="y", labelsize=9, colors=TEXTO)
        FigureCanvasTkAgg(fig2, master=p2).get_tk_widget().pack(fill="x", padx=4)
        separador(self, pady=(10, 0))

        # Fila 2: alertas + nota según días de entrega
        fila2 = ctk.CTkFrame(self, fg_color="transparent")
        fila2.pack(fill="x", padx=32, pady=(0, 24))
        fila2.grid_columnconfigure(0, weight=3, uniform="f2")
        fila2.grid_columnconfigure(1, weight=2, uniform="f2")
        pa = panel(fila2)
        pa.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        titulo_panel(pa, "Requiere atención", "generado a partir de los datos")
        self.alertas = ctk.CTkFrame(pa, fg_color="transparent")
        self.alertas.pack(fill="x", padx=4, pady=(2, 0))

        reciente = v[(v.mes > ultimo - 3) & (v.mes <= ultimo)]
        reg = reciente.groupby("region").atrasado.mean().sort_values(ascending=False)
        top = v.groupby("categoria").valor.sum().nlargest(15).index
        cat = v[v.categoria.isin(top)]
        var_cat = (cat[cat.mes == ultimo].groupby("categoria").valor.sum() /
                   cat[cat.mes == previo].groupby("categoria").valor.sum() - 1).dropna().sort_values()
        vend = reciente.groupby("vendedor").agg(n=("atrasado", "size"), atraso=("atrasado", "mean"))
        vend_mal = int(((vend.n >= 10) & (vend.atraso > 0.10)).sum())
        self.lista_alertas = [
            ("bandeja", COBRE, "", "", "Abrir", lambda: app.ir("ia", urgentes=True)),
            ("reg", COBRE, f"Atrasos altos en el {reg.index[0]}",
             f"{pct(reg.iloc[0])} de los pedidos de los últimos 3 meses llegó tarde (promedio "
             f"{pct(reciente.atrasado.mean())}).", "Ver", lambda: app.ir("analisis", region=reg.index[0])),
            ("vend", OCRE, f"{vend_mal} vendedores con más de 10% de atrasos",
             "Con al menos 10 pedidos en 3 meses; el Seller Center les envía un plan de mejora.", "Ver",
             lambda: app.ir("canales")),
            ("cat", OCRE, f"«{var_cat.index[0]}» cayó {pct(abs(var_cat.iloc[0]), 0)} en el mes",
             f"Ventas de {MESES_LARGOS[ultimo.month - 1]} frente a {MESES_LARGOS[previo.month - 1]}.", "Ver",
             lambda: app.ir("analisis", categoria=var_cat.index[0])),
        ]
        if d.tema_alza:
            t, antes, ahora = d.tema_alza
            self.lista_alertas.insert(1, (
                "alza", COBRE, f"«{t}» crece entre los reclamos",
                f"De {pct(antes, 0)} a {pct(ahora, 0)} de las reseñas negativas en los últimos 3 meses.", "Ver",
                lambda: app.ir("voz")))
        self.pintar_alertas()

        p4 = panel(fila2)
        p4.grid(row=0, column=1, sticky="nsew")
        titulo_panel(p4, "Nota según días de entrega", "promedio 1–5 · 12 meses")
        tramos = pd.cut(anio.dias_entrega, [-1, 7, 14, 21, 30, 1000], labels=["0–7", "8–14", "15–21", "22–30", "+30"])
        nota_t = anio.groupby(tramos, observed=False).nota.mean()
        fig3 = Figure(figsize=(4.8, 2.4), dpi=100, facecolor=BLANCO)
        fig3.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.14)
        ax3 = fig3.add_subplot(111)
        ax3.bar(nota_t.index.astype(str), nota_t.values, width=0.58,
                color=[PETROLEO if (pd.notna(x) and x >= 4) else COBRE for x in nota_t.values])
        for i, val in enumerate(nota_t.values):
            if pd.notna(val):
                ax3.text(i, val + 0.08, num(val, 1), ha="center", fontsize=9, color=TEXTO)
        ax3.axhline(4, color=TEXTO_2, lw=0.8, ls=(0, (4, 3)))
        ax3.set_ylim(0, 5.3)
        ax3.set_yticks([])
        ax3.grid(False)
        ax3.tick_params(axis="x", labelsize=8.5)
        ax3.set_xlabel("días desde la compra", fontsize=8)
        FigureCanvasTkAgg(fig3, master=p4).get_tk_widget().pack(fill="x", padx=4)

    def enviar_resumen(self):
        self.app.enviar_telegram(telegram_bot.mensaje_resumen(self.periodo, self.kpis_resumen, self.alertas_actuales),
                                 self.lbl_tg)

    def pintar_alertas(self):
        self.alertas_actuales = []
        for w in self.alertas.winfo_children():
            w.destroy()
        res = self.app.paginas["ia"].resultados if "ia" in self.app.paginas else pd.DataFrame()
        for clave, color, titulo, detalle, accion, cmd in self.lista_alertas:
            if clave == "bandeja":
                if res.empty:
                    continue
                ia = self.app.paginas["ia"]
                urg = ia.pendientes_alta()
                if urg.empty:
                    hubo = int((res.prioridad == "Alta").sum())
                    titulo = "Sin reclamos urgentes pendientes"
                    detalle = (f"Los {hubo} urgentes del lote ya fueron respondidos." if hubo else
                               f"La IA clasificó {len(res)} mensajes nuevos y ninguno es de prioridad alta.")
                else:
                    partes = [f"{n} por {t.lower()}" for t, n in urg.tema.value_counts().items()]
                    motivo = ", ".join(partes[:-1]) + (" y " if len(partes) > 1 else "") + partes[-1]
                    titulo = (f"{len(urg)} reclamo{'s' if len(urg) != 1 else ''} urgente{'s' if len(urg) != 1 else ''}"
                              f" por aprobar: {motivo}")
                    detalle = (f"De {len(res)} mensajes recibidos hasta las {ia.recibido:%H:%M}; el primero vence a "
                               f"las {urg.limite.min():%H:%M}.")
            self.alertas_actuales.append((titulo, detalle))
            f = ctk.CTkFrame(self.alertas, fg_color="transparent")
            f.pack(fill="x", pady=7)
            ctk.CTkFrame(f, width=3, height=38, corner_radius=0, fg_color=color).pack(side="left", padx=(0, 14))
            txt = ctk.CTkFrame(f, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(txt, text=titulo, font=(CUERPO_SB, 13), text_color=TEXTO, anchor="w").pack(fill="x")
            ctk.CTkLabel(txt, text=detalle, font=(CUERPO, 12), text_color=TEXTO_2, anchor="w", justify="left",
                         wraplength=640).pack(fill="x")
            ctk.CTkButton(f, text=f"{accion}  →", command=cmd, width=70, height=28, fg_color="transparent",
                          hover_color="#F1EEE6", text_color=TINTA, font=(CUERPO_SB, 12)).pack(side="right")


# ---------------------------------------------------------------- Analítica
class PaginaAnalisis(ctk.CTkScrollableFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color=BLANCO, corner_radius=10)
        self.app = app
        d = app.datos
        self.d = d
        acciones = encabezado(self, "Analítica comercial", f"{ESPACIO}  ·  ventas, logística y pagos")
        # Segmentadores (slicers) en el encabezado, como en un reporte de Power BI
        ctk.CTkButton(acciones, text="Limpiar", command=self.limpiar, fg_color="transparent", hover_color="#F1EEE6",
                      text_color=TEXTO_2, font=(CUERPO_SB, 11), width=70).pack(side="right", padx=(6, 0))
        boton(acciones, "Exportar a Excel", self.exportar, principal=False, width=140).pack(side="right", padx=(14, 0))
        top = d.ventas.groupby("categoria").valor.sum().nlargest(20).index.tolist()
        self.f_cat = selector(acciones, ["Todas las categorías"] + sorted(top), self.actualizar, 230)
        self.f_cat.pack(side="right", padx=(6, 0))
        self.f_region = selector(acciones, ["Todas las regiones"] + sorted(d.ventas.region.dropna().unique()),
                                 self.actualizar, 170)
        self.f_region.pack(side="right", padx=(6, 0))
        self.f_anio = selector(acciones, ["Todos los años", "2017", "2018"], self.actualizar, 140)
        self.f_anio.pack(side="right")

        self.kpi = FranjaKPI(self, [
            ("ventas", "Ventas", TINTA), ("pedidos", "Pedidos", TINTA), ("ticket", "Ticket promedio", TINTA),
            ("nota", "Nota promedio", PETROLEO), ("atraso", "Entregas atrasadas", COBRE),
            ("dias", "Días de entrega", TINTA),
        ])
        self.kpi.pack(fill="x", padx=36, pady=(10, 0))
        separador(self, pady=(18, 0))

        cg = panel(self)
        cg.pack(fill="x", padx=28, pady=(0, 4))
        self.fig = Figure(figsize=(12, 8.2), dpi=100, facecolor=BLANCO)
        self.canvas = FigureCanvasTkAgg(self.fig, master=cg)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        separador(self)

        self.ph = panel(self)
        self.ph.pack(fill="x", padx=32, pady=(0, 30))
        titulo_panel(self.ph, "Insights", "se recalculan con cada filtro")
        self.hallazgos = ctk.CTkFrame(self.ph, fg_color="transparent")
        self.hallazgos.pack(fill="x", padx=4, pady=(4, 16))
        self.actualizar()

    TODOS_ANIOS, TODAS_REGIONES, TODAS_CATS = "Todos los años", "Todas las regiones", "Todas las categorías"

    def limpiar(self):
        self.f_anio.set(self.TODOS_ANIOS)
        self.f_region.set(self.TODAS_REGIONES)
        self.f_cat.set(self.TODAS_CATS)
        self.actualizar()

    def aplicar(self, region=None, categoria=None):
        self.f_anio.set(self.TODOS_ANIOS)
        self.f_region.set(region or self.TODAS_REGIONES)
        if categoria and categoria in self.f_cat.cget("values"):
            self.f_cat.set(categoria)
        else:
            self.f_cat.set(self.TODAS_CATS)
        self.actualizar()

    def filtrado(self):
        v = self.d.ventas
        if self.f_anio.get() != self.TODOS_ANIOS:
            v = v[v.anio == int(self.f_anio.get())]
        if self.f_region.get() != self.TODAS_REGIONES:
            v = v[v.region == self.f_region.get()]
        if self.f_cat.get() != self.TODAS_CATS:
            v = v[v.categoria == self.f_cat.get()]
        return v

    def actualizar(self, *_):
        v = self.filtrado()
        self.fig.clear()
        for w in self.hallazgos.winfo_children():
            w.destroy()
        if v.empty:
            for k in self.kpi.valores:
                self.kpi.set(k, "—")
            self.canvas.draw()
            return

        meses = v.mes.nunique()
        self.kpi.set("ventas", millones(v.valor.sum()), f"Promedio mensual {millones(v.valor.sum() / meses)}")
        self.kpi.set("pedidos", num(len(v)), f"{num(v.cliente.nunique())} clientes únicos")
        self.kpi.set("ticket", f"R$ {num(v.valor.mean(), 0)}", f"Flete promedio R$ {num(v.flete.mean(), 0)}")
        self.kpi.set("nota", num(v.nota.mean(), 2), f"{pct((v.nota <= 2).mean())} con nota 1–2")
        self.kpi.set("atraso", pct(v.atrasado.mean()), "Meta: bajo 5%")
        self.kpi.set("dias", num(v.dias_entrega.mean(), 1), f"Mediana {num(v.dias_entrega.median(), 0)} días")

        gs = self.fig.add_gridspec(2, 2, hspace=0.62, wspace=0.42, left=0.07, right=0.97, top=0.9, bottom=0.08)
        ax1, ax2 = self.fig.add_subplot(gs[0, 0]), self.fig.add_subplot(gs[0, 1])
        ax3, ax4 = self.fig.add_subplot(gs[1, 0]), self.fig.add_subplot(gs[1, 1])

        mensual = v.groupby("mes").valor.sum()
        peak = mensual.values.argmax()
        colores = [COBRE if i == peak else TINTA for i in range(len(mensual))]
        ax1.bar(range(len(mensual)), mensual.values / 1e3, color=colores, width=0.72)
        ax1.set_xticks(range(len(mensual))[::2], [mes_txt(p) for p in mensual.index][::2], fontsize=8)
        ax1.annotate(f"{mes_txt(mensual.index[peak])}\nR$ {num(mensual.values[peak] / 1e3)} mil",
                     (peak, mensual.values[peak] / 1e3), xytext=(0, 6), textcoords="offset points", ha="center",
                     fontsize=8, color=COBRE)
        ax1.set_ylim(0, mensual.max() / 1e3 * 1.25)
        estilo_ejes(ax1, "Ventas mensuales", "Miles de R$ · mes peak en cobre")

        cats = v.groupby("categoria").valor.sum().nlargest(8).sort_values()
        ax2.barh(cats.index, cats.values / 1e3, color=[PIZARRA] * (len(cats) - 1) + [TINTA], height=0.62)
        for i, val in enumerate(cats.values):
            ax2.text(val / 1e3, i, f"  {num(val / 1e3)}", va="center", fontsize=8, color=TEXTO)
        ax2.grid(axis="y", visible=False)
        ax2.grid(axis="x", visible=True)
        ax2.set_xlim(0, cats.max() / 1e3 * 1.18)
        ax2.tick_params(axis="y", labelsize=8.5, colors=TEXTO)
        estilo_ejes(ax2, "Categorías que más venden", "Miles de R$ · top 8")

        tramos = pd.cut(v.dias_entrega, [-1, 7, 14, 21, 30, 1000], labels=["0–7", "8–14", "15–21", "22–30", "+30"])
        nota_t = v.groupby(tramos, observed=False).nota.mean()
        ax3.bar(nota_t.index.astype(str), nota_t.values, width=0.62,
                color=[PETROLEO if (pd.notna(x) and x >= 4) else COBRE for x in nota_t.values])
        for i, val in enumerate(nota_t.values):
            if pd.notna(val):
                ax3.text(i, val + 0.08, num(val, 1), ha="center", fontsize=10, color=TEXTO)
        ax3.axhline(4, color=TEXTO_2, lw=0.9, ls=(0, (4, 3)))
        ax3.text(4.45, 4.06, "meta 4,0", fontsize=8, color=TEXTO_2, ha="right", va="bottom")
        ax3.set_ylim(0, 5.3)
        ax3.set_xlabel("Días desde la compra hasta la entrega", fontsize=8.5)
        estilo_ejes(ax3, "Nota del cliente según días de entrega", "Promedio 1–5 · bajo la meta en cobre")

        pagos = v.pago.value_counts(normalize=True).sort_values()
        ax4.barh(pagos.index, pagos.values * 100, height=0.55,
                 color=[COBRE if k == "Boleto bancario" else (TINTA if k == "Tarjeta de crédito" else PIZARRA)
                        for k in pagos.index])
        for i, val in enumerate(pagos.values):
            ax4.text(val * 100, i, f"  {pct(val, 0)}", va="center", fontsize=9, color=TEXTO)
        ax4.grid(axis="y", visible=False)
        ax4.grid(axis="x", visible=True)
        ax4.set_xlim(0, 100)
        ax4.tick_params(axis="y", labelsize=8.5, colors=TEXTO)
        estilo_ejes(ax4, "Medios de pago", "% de pedidos · boleto = pago diferido")

        self.canvas.draw()

        for i, (titulo, hallazgo, decision) in enumerate(self.generar_hallazgos(v, mensual, cats), start=1):
            if i > 1:
                linea(self.hallazgos)
            fila = ctk.CTkFrame(self.hallazgos, fg_color="transparent")
            fila.pack(fill="x", pady=10)
            fila.grid_columnconfigure(1, weight=1, uniform="h")
            fila.grid_columnconfigure(2, weight=1, uniform="h")
            ctk.CTkLabel(fila, text=f"{i:02d}", font=(DISPLAY_SB, 24), text_color=COBRE, width=52, anchor="nw").grid(
                row=0, column=0, rowspan=2, sticky="nw")
            ctk.CTkLabel(fila, text=titulo, font=(DISPLAY_SB, 14), text_color=TINTA, anchor="w").grid(
                row=0, column=1, columnspan=2, sticky="w")
            ctk.CTkLabel(fila, text=hallazgo, font=(CUERPO, 12), text_color=TEXTO, anchor="nw", justify="left",
                         wraplength=520).grid(row=1, column=1, sticky="nw", padx=(0, 24))
            dec = ctk.CTkFrame(fila, fg_color="transparent")
            dec.grid(row=1, column=2, sticky="nw")
            rotulo(dec, "Acción recomendada", PETROLEO, 9).pack(anchor="w")
            ctk.CTkLabel(dec, text=decision, font=(CUERPO, 12), text_color=TEXTO, anchor="w", justify="left",
                         wraplength=520).pack(anchor="w")

    def generar_hallazgos(self, v, mensual, cats):
        h = []
        if len(mensual):
            peak = mensual.idxmax()
            h.append(("Estacionalidad", f"El mes de mayor venta fue {mes_txt(peak)} con R$ {num(mensual.max())}, "
                                        "impulsado por Black Friday.",
                      "Planificar stock, personal y campañas con seis semanas de anticipación para las fechas peak."))
        if len(cats):
            h.append(("Categoría líder", f"«{cats.index[-1]}» concentra {pct(cats.iloc[-1] / v.valor.sum())} de las "
                                         "ventas del período filtrado.",
                      "Concentrar la inversión publicitaria en esta categoría y negociar mejores condiciones con sus "
                      "vendedores."))
        a, ok = v[v.atrasado == 1].nota.mean(), v[v.atrasado == 0].nota.mean()
        if pd.notna(a) and pd.notna(ok):
            h.append(("Logística y satisfacción", f"Los pedidos atrasados reciben nota {num(a, 1)} frente a "
                                                  f"{num(ok, 1)} de los puntuales; {pct(v.atrasado.mean())} llega tarde.",
                      "Activar el aviso proactivo por WhatsApp y medir a cada vendedor por cumplimiento de plazos."))
        b = (v.pago == "Boleto bancario").mean()
        h.append(("Cobranza", f"{pct(b)} de los pedidos se paga con boleto bancario, un pago diferido que puede "
                              "quedar sin completarse.",
                  "Mantener activa la regla de recordatorio de pago por email a las 48 horas."))
        rec = (v.groupby("cliente").size() > 1).mean()
        h.append(("Fidelización", f"Solo {pct(rec)} de los clientes compró más de una vez en el período.",
                  "Usar el CRM para campañas post-compra: cupones, email segmentado y programa de referidos."))
        if self.f_region.get() == self.TODAS_REGIONES:
            h.append(("Cobertura territorial", f"El Sudeste concentra {pct((v.region == 'Sudeste').mean())} de los "
                                               "pedidos; Norte y Nordeste tienen los plazos más largos.",
                      "Operar centros de distribución en el Sudeste y ajustar los plazos prometidos en las regiones "
                      "lejanas."))
        return h

    def exportar(self):
        v = self.filtrado()
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile=f"informe_ventas_{dt.date.today()}.xlsx")
        if not ruta:
            return
        with pd.ExcelWriter(ruta) as xw:
            pd.DataFrame({
                "Indicador": ["Ventas totales (R$)", "Pedidos", "Ticket promedio (R$)", "Nota promedio",
                              "% entregas atrasadas", "Días promedio de entrega"],
                "Valor": [round(v.valor.sum(), 2), len(v), round(v.valor.mean(), 2), round(v.nota.mean(), 2),
                          round(v.atrasado.mean() * 100, 2), round(v.dias_entrega.mean(), 1)],
            }).to_excel(xw, sheet_name="KPIs", index=False)
            m = v.groupby("mes").agg(ventas=("valor", "sum"), pedidos=("valor", "size"), nota=("nota", "mean"))
            m.index = m.index.astype(str)
            m.round(2).to_excel(xw, sheet_name="Mensual")
            v.groupby("categoria").agg(ventas=("valor", "sum"), pedidos=("valor", "size"), nota=("nota", "mean"))\
                .sort_values("ventas", ascending=False).round(2).to_excel(xw, sheet_name="Categorías")
            v.groupby("estado").agg(ventas=("valor", "sum"), pedidos=("valor", "size"),
                                    atraso=("atrasado", "mean")).round(3).to_excel(xw, sheet_name="Estados")
        messagebox.showinfo(APP_NOMBRE, f"Informe guardado en:\n{ruta}")


# ---------------------------------------------------------------- Bandeja IA
class PaginaIA(ctk.CTkScrollableFrame):
    COLS = [("n", "N°", 44), ("mensaje", "Mensaje del cliente", 330), ("sent", "Sentimiento", 96),
            ("tema", "Tema detectado", 190), ("prio", "Prioridad", 76), ("canal", "Canal de respuesta", 160),
            ("estado", "Estado", 118)]
    ESTADO = ("llegada", "limite", "estado", "respondido_por", "respondido_en", "respuesta_enviada")

    def __init__(self, padre, app):
        super().__init__(padre, fg_color=BLANCO, corner_radius=10)
        self.app = app
        d = app.datos
        self.d = d
        self.resultados = pd.DataFrame()
        acciones = encabezado(self, "Bandeja IA")
        boton(acciones, "Exportar tickets al CRM", self.exportar, principal=False, width=190).pack(side="right",
                                                                                                 padx=(8, 0))
        boton(acciones, "Procesar bandeja", self.procesar, width=150).pack(side="right", padx=(8, 0))
        self.n_msg = selector(acciones, ["10", "25", "50", "100", "500"], ancho=80)
        self.n_msg.set("25")
        self.n_msg.pack(side="right", padx=(8, 0))
        rotulo(acciones, "Mensajes").pack(side="right")

        estado = ctk.CTkFrame(self, fg_color="transparent")
        estado.pack(fill="x", padx=36, pady=(0, 10))
        pastilla(estado, "  IA ACTIVA  ", PETROLEO).pack(side="left")
        ctk.CTkLabel(estado, text=f"Modelo de sentimiento v1 · TF-IDF + regresión logística · {pct(d.precision, 0)} de "
                                  f"acierto en {num(d.n_test)} reseñas no vistas", font=(CUERPO, 12),
                     text_color=TEXTO_2).pack(side="left", padx=12)
        self.lbl_tg = ctk.CTkLabel(estado, text="", font=(CUERPO_SB, 12), text_color=TEXTO_2)
        self.lbl_tg.pack(side="right")
        # De dónde viene el lote: se dice explícitamente que es una simulación con reseñas reales
        self.lbl_lote = ctk.CTkLabel(self, text="", font=(CUERPO, 12), text_color=TEXTO_2, anchor="w")
        self.lbl_lote.pack(fill="x", padx=36, pady=(0, 8))

        self.kpi = FranjaKPI(self, [
            ("proc", "Procesados", TINTA), ("alta", "Prioridad alta", COBRE), ("resp", "Respondidos", PETROLEO),
            ("primera", "Primera respuesta", TINTA), ("acierto", "Coincide con nota real", PETROLEO),
            ("ahorro", "Tiempo ahorrado", TINTA),
        ])
        self.kpi.pack(fill="x", padx=32, pady=(0, 12))

        # Atender primero: solo los urgentes del lote, con su plazo
        p_urg = panel(self)
        p_urg.pack(fill="x", padx=32, pady=(0, 10))
        cab = ctk.CTkFrame(p_urg, fg_color="transparent")
        cab.pack(fill="x", padx=4, pady=(6, 4))
        ctk.CTkLabel(cab, text="Atender primero", font=(DISPLAY_SB, 15), text_color=TINTA).pack(side="left")
        self.lbl_urg = ctk.CTkLabel(cab, text="", font=(CUERPO_SB, 12), text_color=COBRE)
        self.lbl_urg.pack(side="left", padx=(12, 0), pady=(2, 0))
        self.lista_urg = ctk.CTkFrame(p_urg, fg_color="transparent")
        self.lista_urg.pack(fill="x", padx=4)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="x", padx=32, pady=(0, 30))
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=2)

        ct = panel(cuerpo)
        ct.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        f = titulo_panel(ct, "Entrada")
        self.filtro = ctk.CTkSegmentedButton(
            f, values=["Todos", "Pendientes", "Alta", "Media", "Baja"], command=lambda _: self.pintar_tabla(),
            corner_radius=3,
            height=26, font=(CUERPO_SB, 11), fg_color="#E6E0D2", selected_color=TINTA, selected_hover_color=TINTA_2,
            unselected_color="#A3ADB8", unselected_hover_color="#8A97A5", text_color="white",
            text_color_disabled=TEXTO_2)
        self.filtro.set("Todos")
        self.filtro.pack(side="right")
        rotulo(f, "Mostrar", size=9).pack(side="right", padx=8)
        marco = ctk.CTkFrame(ct, fg_color="transparent")
        marco.pack(fill="both", expand=True, padx=20, pady=(12, 18))
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in self.COLS], show="headings", selectmode="browse",
                                  height=15)
        for c, t, w in self.COLS:
            self.tabla.heading(c, text=t, anchor="w" if c in ("mensaje", "tema", "canal") else "center")
            self.tabla.column(c, width=w, minwidth=40, stretch=c == "mensaje",
                              anchor="w" if c in ("mensaje", "tema", "canal") else "center")
        self.tabla.tag_configure("Alta", background=TINTE_ALTA)
        self.tabla.tag_configure("Media", background=TINTE_MEDIA)
        self.tabla.tag_configure("Baja", background=TINTE_BAJA)
        self.tabla.tag_configure("hecho", foreground="#8A8577")   # ya respondido
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.ver_detalle)

        # Ficha del ticket
        tk_ = panel(cuerpo)
        tk_.grid(row=0, column=1, sticky="nsew")
        self.cab_ticket = ctk.CTkFrame(tk_, fg_color=TINTA, corner_radius=0, height=64)
        self.cab_ticket.pack(fill="x", padx=1, pady=(1, 0))
        self.lbl_ticket = ctk.CTkLabel(self.cab_ticket, text="TICKET", font=(DISPLAY_SB, 18), text_color="white")
        self.lbl_ticket.pack(side="left", padx=20, pady=16)
        self.lbl_prio = ctk.CTkLabel(self.cab_ticket, text="", font=(CUERPO_SB, 11), text_color="white",
                                     fg_color=COBRE, corner_radius=3, width=110, height=26)
        self.lbl_prio.pack(side="right", padx=20)

        self.campos = {}
        ficha = ctk.CTkFrame(tk_, fg_color="transparent")
        ficha.pack(fill="x", padx=20, pady=(14, 4))
        for i, (clave, etiqueta) in enumerate([("sent", "Sentimiento"), ("nota", "Nota del cliente"),
                                               ("tema", "Tema"), ("area", "Área"), ("canal", "Canal"),
                                               ("sla", "Plazo")]):
            c = ctk.CTkFrame(ficha, fg_color="transparent")
            c.grid(row=i // 2, column=i % 2, sticky="nw", pady=(0, 10))
            ficha.grid_columnconfigure(i % 2, weight=1, uniform="t")
            rotulo(c, etiqueta, size=9).pack(anchor="w")
            self.campos[clave] = ctk.CTkLabel(c, text="—", font=(CUERPO_SB, 12), text_color=TEXTO, anchor="w",
                                              justify="left", wraplength=260)
            self.campos[clave].pack(anchor="w")
        rotulo(tk_, "Por qué la IA decidió esto").pack(fill="x", padx=20, pady=(2, 4))
        self.chips = ctk.CTkFrame(tk_, fg_color="transparent")
        self.chips.pack(fill="x", padx=20, pady=(0, 12))
        linea(tk_, padx=20)
        rotulo(tk_, "Mensaje original").pack(fill="x", padx=20, pady=(12, 4))
        self.txt_msg = ctk.CTkTextbox(tk_, height=84, font=(CUERPO, 12), wrap="word", fg_color=CAMPO,
                                      corner_radius=3, border_width=0, text_color=TEXTO)
        self.txt_msg.pack(fill="x", padx=20)
        cab_resp = ctk.CTkFrame(tk_, fg_color="transparent")
        cab_resp.pack(fill="x", padx=20, pady=(12, 4))
        rotulo(cab_resp, "Respuesta sugerida · editable").pack(side="left")
        self.idioma = ctk.CTkSegmentedButton(
            cab_resp, values=["Español", "Português"], command=lambda _: self.pintar_respuesta(), corner_radius=3,
            height=24, font=(CUERPO_SB, 10), fg_color="#E6E0D2", selected_color=TINTA, selected_hover_color=TINTA_2,
            unselected_color="#A3ADB8", unselected_hover_color="#8A97A5", text_color="white")
        self.idioma.set("Español")
        self.idioma.pack(side="right")
        self.actual = None
        self.txt_resp = ctk.CTkTextbox(tk_, height=110, font=(CUERPO, 12), wrap="word", fg_color="#EEF2F6",
                                       corner_radius=3, border_width=0, text_color=TEXTO)
        self.txt_resp.pack(fill="x", padx=20)
        envio = ctk.CTkFrame(tk_, fg_color="transparent")
        envio.pack(fill="x", padx=20, pady=12)
        self.btn_enviar = boton(envio, "Enviar respuesta", self.enviar, width=150)
        self.btn_enviar.pack(side="right")
        boton(envio, "Copiar", self.copiar, principal=False, width=80).pack(side="right", padx=(0, 8))
        self.lbl_envio = ctk.CTkLabel(envio, text="", font=(CUERPO_SB, 11), text_color=TEXTO_2, anchor="w",
                                      justify="left", wraplength=260)
        self.lbl_envio.pack(side="left", fill="x", expand=True)

        linea(tk_, padx=20)
        rotulo(tk_, "Probar con un mensaje (el modelo entiende portugués)").pack(fill="x", padx=20, pady=(12, 6))
        prueba = ctk.CTkFrame(tk_, fg_color="transparent")
        prueba.pack(fill="x", padx=20, pady=(0, 18))
        self.entrada = ctk.CTkEntry(prueba, placeholder_text="Ej: o produto chegou quebrado e ninguém responde",
                                    corner_radius=3, height=34, border_color=LINEA, fg_color=CAMPO,
                                    font=(CUERPO, 12))
        self.entrada.pack(side="left", fill="x", expand=True)
        self.entrada.bind("<Return>", lambda e: self.analizar_propio())
        boton(prueba, "Analizar", self.analizar_propio, width=90).pack(side="left", padx=(8, 0))

    # --- núcleo del proceso automatizado
    def clasificar(self, textos):
        proba = self.d.modelo.predict_proba(textos)
        clases = self.d.modelo.classes_
        activos = self.app.canales
        sents = [clases[p.argmax()] for p in proba]
        palabras = self.d.explicar(textos, sents)
        filas = []
        hoy = dt.date.today().strftime("%y%m%d")
        for i, (texto, p, sent, pal) in enumerate(zip(textos, proba, sents, palabras), start=1):
            tema, area = detectar_tema(texto)
            if sent == "Positivo":
                tema, area = "Elogio / comentario positivo", "Marketing"
            prio, canal, sla = decidir(sent, tema, activos)
            ticket = f"TCK-{hoy}-{i:04d}"
            wa = canal.startswith("WhatsApp")
            clave = "Positivo" if sent == "Positivo" else (tema if tema in RESPUESTAS else "General")
            horas = sla.replace("h", "horas")
            filas.append({"ticket": ticket, "mensaje": texto, "sentimiento": sent, "confianza": p.max(),
                          "tema": tema, "area": area, "prioridad": prio, "canal": canal, "sla": sla,
                          "palabras_clave": ", ".join(pal),
                          "respuesta": RESPUESTAS[clave].format(ticket=ticket, sla=horas,
                                                                via="por WhatsApp" if wa else "por correo"),
                          "respuesta_pt": RESPUESTAS_PT[clave].format(ticket=ticket, sla=horas,
                                                                      via="pelo WhatsApp" if wa else "por e-mail")})
        return pd.DataFrame(filas)

    def aviso_telegram(self, n, error):
        if error:
            self.lbl_tg.configure(text=f"Telegram: {error}", text_color=COBRE)
        elif n:
            self.lbl_tg.configure(text=f"Telegram · {n} aviso{'s' if n != 1 else ''} de tickets críticos enviado"
                                       f"{'s' if n != 1 else ''}", text_color=PETROLEO)

    def procesar(self, avisar=True):
        n = int(self.n_msg.get())
        muestra = self.d.resenas.sample(n)
        t0 = time.perf_counter()
        res = self.clasificar(muestra.texto.tolist())
        self.seg = time.perf_counter() - t0
        res["nota_real"] = muestra.nota.values
        res["sentimiento_real"] = muestra.sentimiento.values
        res["fecha_resena"] = muestra.fecha.values
        self.recibido = dt.datetime.now()
        self.avisados_vencer = set()   # tickets ya recordados por Telegram
        # Simulación: los mensajes llegaron a lo largo de la última hora y media
        minutos = sorted((random.uniform(0, 90) for _ in range(n)), reverse=True)
        res["llegada"] = [self.recibido - dt.timedelta(minutes=m) for m in minutos]
        res["limite"] = [ll + plazo(s) for ll, s in zip(res.llegada, res.sla)]
        # Respuesta automática para la prioridad baja; media y alta esperan a un agente (alta: aprobación)
        auto = (res.prioridad == "Baja").tolist()
        res["estado"] = ["Respondido" if a else "Pendiente" for a in auto]
        res["respondido_por"] = ["Automático" if a else "" for a in auto]
        res["respondido_en"] = pd.to_datetime([ll + dt.timedelta(seconds=5) if a else pd.NaT
                                               for ll, a in zip(res.llegada, auto)])
        res["respuesta_enviada"] = [r if a else "" for r, a in zip(res.respuesta, auto)]
        self.resultados = res
        self.lbl_lote.configure(text=f"{n} mensajes recibidos entre las {res.llegada.min():%H:%M} y las "
                                     f"{self.recibido:%H:%M}  ·  {sum(auto)} respondidos automáticamente  ·  simulación "
                                     "con reseñas reales de clientes que la IA no vio al entrenar")
        self.refrescar()
        if avisar:
            self.app.avisar_telegram(res.to_dict("records"), self.aviso_telegram)

    def pendientes_alta(self):
        r = self.resultados
        return r[(r.prioridad == "Alta") & (r.estado != "Respondido")] if not r.empty else r

    def refrescar(self, seleccion=None):
        """Vuelve a pintar tabla, urgentes, KPIs, insignia y alertas tras un cambio en la bandeja."""
        self.pintar_tabla()
        if seleccion is not None and str(seleccion) in self.tabla.get_children():
            self.tabla.selection_set(str(seleccion))
            self.tabla.see(str(seleccion))
        self.pintar_urgentes()
        self.actualizar_kpis()
        self.app.bandeja_actualizada(len(self.pendientes_alta()))

    def actualizar_kpis(self):
        res = self.resultados
        n = len(res)
        resp = res[res.estado == "Respondido"]
        auto = int((resp.respondido_por == "Automático").sum())
        alta = int((res.prioridad == "Alta").sum())
        pend = len(self.pendientes_alta())
        self.kpi.set("proc", num(n), f"en {num(self.seg, 2)} segundos")
        self.kpi.set("alta", num(alta), f"{pend} por aprobar" if pend else ("todas respondidas" if alta else "ninguna"))
        self.kpi.set("resp", f"{len(resp)} de {n}", f"{auto} automáticas · {len(resp) - auto} por un agente")
        agente = resp[resp.respondido_por != "Automático"]
        if len(agente):
            m = (agente.respondido_en - agente.llegada).mean().total_seconds() / 60
            self.kpi.set("primera", duracion(m), "promedio de los agentes · meta: menos de 2 h")
            self.kpi.valores["primera"].configure(text_color=PETROLEO if m <= 120 else COBRE)
        else:
            self.kpi.set("primera", "—", "aún sin respuestas de un agente")
            self.kpi.valores["primera"].configure(text_color=TINTA)
        self.kpi.set("acierto", pct((res.sentimiento == res.sentimiento_real).mean(), 0), "IA vs. nota del cliente")
        manual_min = n * 3  # supuesto: 3 minutos por mensaje leído, clasificado y respondido a mano
        self.kpi.set("ahorro", f"{num(manual_min / 60, 1)} h" if manual_min >= 60 else f"{manual_min} min",
                     "supuesto: 3 min por mensaje")

    def pintar_urgentes(self, maximo=6):
        for w in self.lista_urg.winfo_children():
            w.destroy()
        res = self.resultados
        if res.empty:
            return
        ahora = dt.datetime.now()
        urg = self.pendientes_alta().sort_values("limite")
        if urg.empty:
            hubo = int((res.prioridad == "Alta").sum())
            self.lbl_urg.configure(text="✓ Todos los urgentes respondidos" if hubo else "", text_color=PETROLEO)
            ctk.CTkLabel(self.lista_urg, text="No hay reclamos urgentes pendientes." if hubo else
                         "Sin reclamos urgentes en este lote.", font=(CUERPO, 12), text_color=TEXTO_2,
                         anchor="w").pack(fill="x", pady=(0, 8))
            return
        self.lbl_urg.configure(text=f"{len(urg)} por aprobar  ·  el primero vence a las {urg.limite.min():%H:%M}",
                               text_color=COBRE)
        for i, r in urg.head(maximo).iterrows():
            f = ctk.CTkFrame(self.lista_urg, fg_color="transparent")
            f.pack(fill="x", pady=4)
            ctk.CTkFrame(f, width=3, height=36, corner_radius=0, fg_color=COBRE).pack(side="left", padx=(0, 12))
            ctk.CTkLabel(f, text=r.ticket, font=(CUERPO_SB, 12), text_color=TEXTO, width=120, anchor="w").pack(
                side="left")
            ctk.CTkLabel(f, text=f"{r.tema}  ·  {r.area}  ·  {r.canal}", font=(CUERPO_SB, 12), text_color=TINTA,
                         width=380, anchor="w").pack(side="left")
            texto = r.mensaje if len(r.mensaje) <= 64 else r.mensaje[:64] + "…"
            ctk.CTkButton(f, text="Ver  →", command=lambda k=i: self.seleccionar(k), width=64, height=28,
                          fg_color="transparent", hover_color="#F1EEE6", text_color=TINTA,
                          font=(CUERPO_SB, 12)).pack(side="right")
            vencido = ahora > r.limite
            ctk.CTkLabel(f, text="VENCIDO" if vencido else f"vence a las {r.limite:%H:%M}", font=(CUERPO_SB, 12),
                         text_color=COBRE).pack(side="right", padx=(12, 8))
            ctk.CTkLabel(f, text=f"llegó {r.llegada:%H:%M}", font=(CUERPO, 11), text_color=TEXTO_2).pack(
                side="right", padx=(12, 0))
            ctk.CTkLabel(f, text=f"«{texto}»", font=(CUERPO, 12), text_color=TEXTO_2, anchor="w").pack(
                side="left", fill="x", expand=True)
        if len(urg) > maximo:
            ctk.CTkButton(self.lista_urg, text=f"y {len(urg) - maximo} más: ver todos los pendientes  →",
                          command=lambda: (self.filtro.set("Pendientes"), self.pintar_tabla()),
                          fg_color="transparent", hover_color="#F1EEE6", text_color=TINTA, font=(CUERPO_SB, 12),
                          anchor="w", height=26).pack(anchor="w")

    def seleccionar(self, i):
        """Abre la ficha de un ticket de la bandeja y lo marca en la tabla."""
        if str(i) not in self.tabla.get_children():
            self.filtro.set("Todos")
            self.pintar_tabla()
        self.tabla.selection_set(str(i))
        self.tabla.see(str(i))

    def ver_urgentes(self):
        self.filtro.set("Alta")
        self.pintar_tabla()

    @staticmethod
    def estado_txt(r, ahora):
        if r.estado == "Respondido":
            return "✓ Automático" if r.respondido_por == "Automático" else "✓ Respondido"
        return "Vencido" if ahora > r.limite else ("Por aprobar" if r.prioridad == "Alta" else "Pendiente")

    def pintar_tabla(self):
        self.tabla.delete(*self.tabla.get_children())
        res = self.resultados
        if res.empty:
            return
        filtro, ahora = self.filtro.get(), dt.datetime.now()
        for i, r in res.iterrows():
            if filtro == "Pendientes" and r.estado == "Respondido":
                continue
            if filtro in ("Alta", "Media", "Baja") and r.prioridad != filtro:
                continue
            etiquetas = (r.prioridad, "hecho") if r.estado == "Respondido" else (r.prioridad,)
            self.tabla.insert("", "end", iid=str(i), tags=etiquetas, values=(
                f"{i + 1:02d}", r.mensaje[:90] + ("…" if len(r.mensaje) > 90 else ""), r.sentimiento, r.tema,
                r.prioridad, r.canal, self.estado_txt(r, ahora)))
        hijos = self.tabla.get_children()
        if hijos:
            self.tabla.selection_set(hijos[0])

    def mostrar(self, r, nota_real=None):
        color = {"Alta": COBRE, "Media": OCRE, "Baja": PETROLEO}[r["prioridad"]]
        self.lbl_ticket.configure(text=r["ticket"])
        self.lbl_prio.configure(text=f"PRIORIDAD {r['prioridad'].upper()}", fg_color=color)
        self.campos["sent"].configure(text=f"{r['sentimiento']} ({pct(r['confianza'], 0)})")
        self.campos["tema"].configure(text=r["tema"])
        self.campos["area"].configure(text=r["area"])
        self.campos["canal"].configure(text=r["canal"])
        self.campos["sla"].configure(text=f"Responder en {r['sla']}")
        self.campos["nota"].configure(text=f"{int(nota_real)} de 5" if nota_real is not None else "Mensaje de prueba")
        for w in self.chips.winfo_children():
            w.destroy()
        pal = [p for p in r["palabras_clave"].split(", ") if p]
        tinte = {"Negativo": TINTE_ALTA, "Neutro": TINTE_MEDIA, "Positivo": "#E3EFEC"}[r["sentimiento"]]
        tono = {"Negativo": COBRE, "Neutro": OCRE, "Positivo": PETROLEO}[r["sentimiento"]]
        for p in pal:
            ctk.CTkLabel(self.chips, text=f"  {p}  ", font=(CUERPO_SB, 11), fg_color=tinte, text_color=tono,
                         corner_radius=3, height=24).pack(side="left", padx=(0, 6))
        if pal:
            ctk.CTkLabel(self.chips, text=f"→ {r['sentimiento'].lower()}", font=(CUERPO, 11),
                         text_color=TEXTO_2).pack(side="left", padx=4)
        else:
            ctk.CTkLabel(self.chips, text="Sin palabras conocidas por el modelo", font=(CUERPO, 11),
                         text_color=TEXTO_2).pack(side="left")
        self.actual = r
        self.txt_msg.delete("1.0", "end")
        self.txt_msg.insert("1.0", r["mensaje"])
        self.pintar_respuesta()
        self.pintar_envio()

    def pintar_envio(self):
        """Estado de envío del ticket abierto y el botón que corresponde."""
        r = self.actual
        if r is None or "estado" not in r:
            self.lbl_envio.configure(text="Mensaje de prueba: no se envía a ningún cliente.", text_color=TEXTO_2)
            self.btn_enviar.configure(text="Enviar respuesta", state="disabled")
        elif r["estado"] == "Respondido":
            a_tiempo = r["respondido_en"] <= r["limite"]
            quien = "automáticamente" if r["respondido_por"] == "Automático" else "por un agente"
            self.lbl_envio.configure(text=f"✓ Enviada {quien} a las {r['respondido_en']:%H:%M} · "
                                          f"{'dentro del plazo' if a_tiempo else 'fuera de plazo'}",
                                     text_color=PETROLEO if a_tiempo else COBRE)
            self.btn_enviar.configure(text="Enviada", state="disabled")
        else:
            vencido = dt.datetime.now() > r["limite"]
            self.lbl_envio.configure(text=(f"Llegó a las {r['llegada']:%H:%M} · " +
                                           ("plazo VENCIDO" if vencido else f"vence a las {r['limite']:%H:%M}")),
                                     text_color=COBRE if (vencido or r["prioridad"] == "Alta") else TEXTO_2)
            self.btn_enviar.configure(text="Aprobar y enviar" if r["prioridad"] == "Alta" else "Enviar respuesta",
                                      state="normal")

    def pintar_respuesta(self):
        if self.actual is None:
            return
        r = self.actual
        if "estado" in r and r["estado"] == "Respondido" and self.idioma.get() == "Español":
            texto = r["respuesta_enviada"] or r["respuesta"]
        else:
            texto = r["respuesta_pt" if self.idioma.get() == "Português" else "respuesta"]
        self.txt_resp.delete("1.0", "end")
        self.txt_resp.insert("1.0", texto)

    def enviar(self):
        """Envía (simulado) la respuesta del ticket abierto: queda registrada con su hora y el plazo cumplido o no."""
        r = self.actual
        if r is None or "estado" not in r or r["estado"] == "Respondido":
            return
        i = r.name
        self.resultados.loc[i, "estado"] = "Respondido"
        self.resultados.loc[i, "respondido_por"] = "Agente"
        self.resultados.loc[i, "respondido_en"] = pd.Timestamp(dt.datetime.now())
        self.resultados.loc[i, "respuesta_enviada"] = self.txt_resp.get("1.0", "end").strip()
        self.refrescar(seleccion=i)
        self.mostrar(self.resultados.loc[i], self.resultados.loc[i, "nota_real"])

    def ver_detalle(self, _=None):
        sel = self.tabla.selection()
        if sel:
            r = self.resultados.loc[int(sel[0])]
            self.mostrar(r, r["nota_real"])

    def analizar_propio(self):
        texto = self.entrada.get().strip()
        if texto:
            r = self.clasificar([texto]).iloc[0]
            self.mostrar(r)
            self.app.avisar_telegram([r.to_dict()], self.aviso_telegram)

    def copiar(self):
        self.clipboard_clear()
        self.clipboard_append(self.txt_resp.get("1.0", "end").strip())

    def exportar(self):
        if self.resultados.empty:
            messagebox.showwarning(APP_NOMBRE, "Primero procesa la bandeja de entrada.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile=f"tickets_crm_{dt.date.today()}.xlsx")
        if ruta:
            self.resultados.to_excel(ruta, index=False)
            messagebox.showinfo(APP_NOMBRE, f"{len(self.resultados)} tickets exportados en:\n{ruta}\n\n"
                                            "Este archivo se puede importar en un CRM (HubSpot, Zoho, Salesforce).")


# ---------------------------------------------------------------- Voz del cliente
COLORES_TEMA = {"No recibido": COBRE, "Retraso en la entrega": OCRE, "Producto incorrecto o incompleto": TINTA,
                "Producto defectuoso": "#7A4B8C", "Otros": PIZARRA}


class PaginaVoz(ctk.CTkScrollableFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color=BLANCO, corner_radius=10)
        self.app = app
        d = app.datos
        voz, rk = d.voz, d.ranking
        acciones = encabezado(self, "Voz del cliente")
        boton(acciones, "Exportar ranking", self.exportar, principal=False, width=150).pack(side="right")
        boton(acciones, "Vendedores en riesgo a Telegram", self.enviar_telegram, principal=False, width=240).pack(
            side="right", padx=(0, 8))
        self.lbl_tg = ctk.CTkLabel(acciones, text="", font=(CUERPO_SB, 11), text_color=TEXTO_2)
        self.lbl_tg.pack(side="right", padx=(0, 12))

        kpi = FranjaKPI(self, [
            ("res", "Reseñas analizadas", TINTA), ("neg", "Negativas según la IA", COBRE),
            ("tema", "Motivo principal", TINTA), ("alza", "Motivo en alza", COBRE),
            ("riesgo", "Vendedores en riesgo", COBRE),
        ])
        kpi.pack(fill="x", padx=32, pady=(0, 12))
        neg = voz[voz.negativo]
        top_tema = neg[neg.tema != "General"].tema.value_counts()
        kpi.set("res", num(len(voz)), f"{mes_txt(voz.mes.min())} a {mes_txt(voz.mes.max())}")
        kpi.set("neg", pct(voz.negativo.mean()), f"{num(len(neg))} reseñas")
        kpi.set("tema", top_tema.index[0], f"{pct(top_tema.iloc[0] / len(neg), 0)} de las negativas")
        if d.tema_alza:
            t, antes, ahora = d.tema_alza
            kpi.set("alza", t, f"{pct(antes, 0)} → {pct(ahora, 0)} de los reclamos (últimos 3 meses)")
        n_riesgo = int((rk.estado == "En riesgo").sum())
        kpi.set("riesgo", num(n_riesgo), f"de {num(len(rk))} con 20+ reseñas")

        # Tendencia
        pt = panel(self)
        pt.pack(fill="x", padx=32, pady=(0, 12))
        titulo_panel(pt, "Tendencia de reclamos")
        fig = Figure(figsize=(12, 3.9), dpi=100, facecolor=BLANCO)
        gs = fig.add_gridspec(1, 2, wspace=0.28, left=0.06, right=0.84, top=0.84, bottom=0.14)
        ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
        mensual = voz.groupby("mes").negativo.mean() * 100
        x = range(len(mensual))
        etiquetas = [mes_txt(p) for p in mensual.index]
        ax1.plot(x, mensual.values, color=COBRE, lw=2.2)
        ax1.fill_between(x, mensual.values, color=COBRE, alpha=0.07)
        ax1.axhline(voz.negativo.mean() * 100, color=TEXTO_2, lw=0.9, ls=(0, (4, 3)))
        ax1.set_xticks(list(x)[::3], etiquetas[::3], fontsize=8)
        ax1.set_ylim(0, mensual.max() * 1.3)
        estilo_ejes(ax1, "Reseñas negativas por mes", "% del total · línea punteada = promedio")
        ip = mensual.values.argmax()
        ax1.annotate(f"{num(mensual.values[ip], 0)}%", (ip, mensual.values[ip]), xytext=(0, 6),
                     textcoords="offset points", ha="center", fontsize=8, color=COBRE)

        temas = [t for t in COLORES_TEMA if t != "Otros"]
        tabla = neg.assign(t=neg.tema.where(neg.tema.isin(temas), "Otros")).groupby(["mes", "t"]).size().unstack(
            fill_value=0)
        tabla = tabla.reindex(columns=temas + ["Otros"], fill_value=0)
        share = tabla.div(tabla.sum(axis=1), axis=0) * 100
        base = None
        for t in share.columns:
            ax2.bar(range(len(share)), share[t].values, bottom=base, color=COLORES_TEMA[t], width=0.78, label=t)
            base = share[t].values if base is None else base + share[t].values
        ax2.set_xticks(range(len(share))[::3], [mes_txt(p) for p in share.index][::3], fontsize=8)
        ax2.set_ylim(0, 100)
        ax2.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=8.5)
        estilo_ejes(ax2, "Motivos de los reclamos", "% de las reseñas negativas de cada mes")
        FigureCanvasTkAgg(fig, master=pt).get_tk_widget().pack(fill="x", padx=10, pady=(4, 10))

        # Ranking de vendedores
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="x", padx=32, pady=(0, 30))
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=2)
        pr = panel(cuerpo)
        pr.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        f = titulo_panel(pr, "Vendedores con más reclamos")
        rotulo(f, f"Promedio: {pct(d.pct_neg_prom, 0)} negativas", size=9).pack(side="right")
        marco = ctk.CTkFrame(pr, fg_color="transparent")
        marco.pack(fill="both", expand=True, padx=20, pady=(12, 18))
        cols = [("v", "Vendedor", 90), ("r", "Reseñas", 70), ("p", "% negativas", 90), ("t", "Motivo principal", 210),
                ("c", "Categoría", 190), ("n", "Nota", 60), ("e", "Estado", 100)]
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in cols], show="headings", selectmode="browse",
                                  height=14)
        for c, t, w in cols:
            izq = c in ("t", "c", "v")
            self.tabla.heading(c, text=t, anchor="w" if izq else "center")
            self.tabla.column(c, width=w, anchor="w" if izq else "center", stretch=c in ("t", "c"))
        self.tabla.tag_configure("En riesgo", background=TINTE_ALTA)
        self.tabla.tag_configure("Observación", background=TINTE_MEDIA)
        self.tabla.tag_configure("Normal", background=BLANCO)
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        for vid, r in rk.head(60).iterrows():
            self.tabla.insert("", "end", iid=str(int(vid)), tags=(str(r.estado),), values=(
                f"V-{int(vid):04d}", num(r.resenas), pct(r.pct_neg, 0), r.tema, r.categoria, num(r.nota, 1),
                r.estado))
        self.tabla.bind("<<TreeviewSelect>>", self.ver_vendedor)

        self.det = panel(cuerpo)
        self.det.grid(row=0, column=1, sticky="nsew")
        hijos = self.tabla.get_children()
        if hijos:
            self.tabla.selection_set(hijos[0])

    def enviar_telegram(self):
        d = self.app.datos
        riesgo = d.ranking[d.ranking.estado == "En riesgo"]
        filas = [(f"V-{int(v):04d}", int(r.resenas), pct(r.pct_neg, 0), r.tema, r.categoria)
                 for v, r in riesgo.head(10).iterrows()]
        self.app.enviar_telegram(telegram_bot.mensaje_vendedores(filas, len(riesgo), len(d.ranking),
                                                                 pct(d.pct_neg_prom, 0)), self.lbl_tg)

    def ver_vendedor(self, _=None):
        sel = self.tabla.selection()
        if not sel:
            return
        vid = int(sel[0])
        d = self.app.datos
        r = d.ranking.loc[vid]
        rv = d.voz[d.voz.vendedor == vid]
        neg = rv[rv.negativo]
        for w in self.det.winfo_children():
            w.destroy()
        cab = ctk.CTkFrame(self.det, fg_color=TINTA, corner_radius=0, height=64)
        cab.pack(fill="x", padx=1, pady=(1, 0))
        ctk.CTkLabel(cab, text=f"Vendedor V-{vid:04d}", font=(DISPLAY_SB, 18), text_color="white").pack(
            side="left", padx=20, pady=16)
        color = {"En riesgo": COBRE, "Observación": OCRE}.get(str(r.estado), PETROLEO)
        ctk.CTkLabel(cab, text=str(r.estado).upper(), font=(CUERPO_SB, 11), text_color="white", fg_color=color,
                     corner_radius=3, width=110, height=26).pack(side="right", padx=20)

        cifras = ctk.CTkFrame(self.det, fg_color="transparent")
        cifras.pack(fill="x", padx=20, pady=(14, 6))
        for i, (k, v) in enumerate([("Reseñas", num(r.resenas)), ("Negativas", pct(r.pct_neg, 0)),
                                    ("Nota", num(r.nota, 1)), ("Categoría", r.categoria)]):
            c = ctk.CTkFrame(cifras, fg_color="transparent")
            c.grid(row=0, column=i, sticky="nw")
            cifras.grid_columnconfigure(i, weight=1 if i < 3 else 2, uniform="v" if i < 3 else None)
            rotulo(c, k, size=9).pack(anchor="w")
            ctk.CTkLabel(c, text=v, font=(DISPLAY_SB, 18 if i < 3 else 13), text_color=TINTA, anchor="w",
                         wraplength=170, justify="left").pack(anchor="w")
        linea(self.det, padx=20)
        rotulo(self.det, "Motivos de sus reclamos").pack(fill="x", padx=20, pady=(12, 6))
        mot = neg.tema.replace("General", "Otro motivo").value_counts(normalize=True).head(4)
        for t, v in mot.items():
            f = ctk.CTkFrame(self.det, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(f, text=t, font=(CUERPO, 11), text_color=TEXTO, anchor="w", width=200).pack(side="left")
            ctk.CTkLabel(f, text=pct(v, 0), font=(CUERPO_SB, 11), text_color=TEXTO, width=40).pack(side="right")
            b = ctk.CTkProgressBar(f, height=8, corner_radius=2, progress_color=COLORES_TEMA.get(t, PIZARRA),
                                   fg_color="#ECE8DE")
            b.set(float(v))
            b.pack(side="left", fill="x", expand=True, padx=8)
        linea(self.det, padx=20, pady=(12, 0))
        rotulo(self.det, "Reclamos recientes").pack(fill="x", padx=20, pady=(12, 4))
        for _, x in neg.sort_values("fecha", ascending=False).head(3).iterrows():
            ctk.CTkLabel(self.det, text=f"«{x.texto[:150]}{'…' if len(x.texto) > 150 else ''}»",
                         font=(CUERPO, 11), text_color=TEXTO, anchor="w", justify="left", wraplength=480,
                         fg_color=CAMPO, corner_radius=3).pack(fill="x", padx=20, pady=3, ipady=6, ipadx=8)
            ctk.CTkLabel(self.det, text=f"{x.fecha:%d-%m-%Y} · {x.tema}", font=(CUERPO, 10), text_color=TEXTO_2,
                         anchor="w").pack(fill="x", padx=20)
        ctk.CTkFrame(self.det, height=14, fg_color="transparent").pack()

    def exportar(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile=f"ranking_vendedores_{dt.date.today()}.xlsx")
        if ruta:
            rk = self.app.datos.ranking.reset_index()
            rk["vendedor"] = rk.vendedor.map(lambda v: f"V-{int(v):04d}")
            rk.rename(columns={"resenas": "reseñas", "pct_neg": "pct_negativas", "tema": "motivo_principal"}).to_excel(
                ruta, index=False)
            messagebox.showinfo(APP_NOMBRE, f"Ranking guardado en:\n{ruta}")


# ---------------------------------------------------------------- Modelo IA: métricas, pruebas y generador
class PaginaModelo(ctk.CTkScrollableFrame):
    COLS = [("id", "ID", 60), ("tipo", "Tipo", 80), ("mensaje", "Mensaje", 300), ("esp", "Esperado", 270),
            ("obt", "Resultado de la IA", 270), ("conf", "Confianza", 80), ("ok", "Resultado", 90)]

    def __init__(self, padre, app):
        super().__init__(padre, fg_color=BLANCO, corner_radius=10)
        self.app = app
        d = app.datos
        self.d = d
        self.extra = []          # casos generados que el usuario agregó a la suite
        self.n_gen, self.ok_gen = 0, 0
        acciones = encabezado(self, "Modelo IA")
        boton(acciones, "Exportar resultados", self.exportar, principal=False, width=160).pack(side="right",
                                                                                            padx=(8, 0))
        boton(acciones, "Ejecutar pruebas", self.ejecutar, width=150).pack(side="right")

        self.kpi = FranjaKPI(self, [
            ("acc", "Exactitud", PETROLEO), ("neg", "Detecta negativos", COBRE), ("pos", "Precisión positivos", TINTA),
            ("suite", "Suite de pruebas", TINTA), ("gen", "Casos generados", TINTA),
        ])
        self.kpi.pack(fill="x", padx=32, pady=(0, 12))
        rep = d.reporte
        self.kpi.set("acc", pct(d.precision, 0), f"en {num(d.n_test)} reseñas no vistas")
        self.kpi.set("neg", pct(rep["Negativo"]["recall"], 0), "de los negativos reales (recall)")
        self.kpi.set("pos", pct(rep["Positivo"]["precision"], 0), "cuando dice positivo, acierta")
        self.kpi.set("gen", "—", "aún no se generan casos")

        # Matriz de confusión + métricas por clase
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=32, pady=(0, 12))
        fila.grid_columnconfigure(0, weight=1, uniform="m")
        fila.grid_columnconfigure(1, weight=1, uniform="m")
        pm = panel(fila)
        pm.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        titulo_panel(pm, "Matriz de confusión", f"{num(d.n_test)} reseñas reales no vistas")
        fig = Figure(figsize=(5.6, 3.4), dpi=100, facecolor=BLANCO)
        ax = fig.add_axes([0.2, 0.12, 0.62, 0.78])
        m = d.matriz
        filas_pct = m / m.sum(axis=1, keepdims=True)
        ax.imshow(filas_pct, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("p", [BLANCO, TINTA]),
                  vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{num(m[i, j])}\n{pct(filas_pct[i, j], 0)}", ha="center", va="center", fontsize=9,
                        color="white" if filas_pct[i, j] > 0.5 else TEXTO)
        ax.set_xticks(range(3), d.etiquetas)
        ax.set_yticks(range(3), d.etiquetas)
        ax.set_xlabel("Lo que dijo la IA", fontsize=9)
        ax.set_ylabel("Nota real del cliente", fontsize=9)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        FigureCanvasTkAgg(fig, master=pm).get_tk_widget().pack(fill="x", padx=10, pady=(4, 10))

        pc = panel(fila)
        pc.grid(row=0, column=1, sticky="nsew")
        titulo_panel(pc, "Por clase")
        t = ctk.CTkFrame(pc, fg_color="transparent")
        t.pack(fill="x", padx=20, pady=(10, 6))
        for j, h in enumerate(["Clase", "Precisión", "Recall", "F1", "Reseñas"]):
            rotulo(t, h, size=9).grid(row=0, column=j, sticky="w", pady=(0, 6))
            t.grid_columnconfigure(j, weight=1)
        for i, c in enumerate(d.etiquetas, start=1):
            r = rep[c]
            debil = r["f1-score"] < 0.5
            for j, v in enumerate([c, pct(r["precision"], 0), pct(r["recall"], 0), num(r["f1-score"], 2),
                                   num(r["support"])]):
                ctk.CTkLabel(t, text=v, font=(CUERPO_SB if j == 0 else CUERPO, 12),
                             text_color=COBRE if (debil and j in (1, 2, 3)) else TEXTO, anchor="w").grid(
                    row=i, column=j, sticky="w", pady=4)
        linea(pc, padx=20, pady=(8, 0))
        rotulo(pc, "Limitaciones detectadas", COBRE, 9).pack(fill="x", padx=20, pady=(10, 2))
        self.lbl_limites = ctk.CTkLabel(pc, text="", font=(CUERPO, 12), text_color=TEXTO, anchor="w", justify="left",
                                        wraplength=560)
        self.lbl_limites.pack(fill="x", padx=20, pady=(0, 16))

        # Generador en vivo
        pg = panel(self)
        pg.pack(fill="x", padx=32, pady=(0, 12))
        f = titulo_panel(pg, "Generar un caso nuevo")
        cuerpo = ctk.CTkFrame(pg, fg_color="transparent")
        cuerpo.pack(fill="x", padx=20, pady=(12, 16))
        ctrl = ctk.CTkFrame(cuerpo, fg_color="transparent")
        ctrl.pack(fill="x")
        rotulo(ctrl, "Escenario").pack(side="left", padx=(0, 8))
        self.escenario = selector(ctrl, ["Aleatorio"] + list(ESCENARIOS), ancho=210)
        self.escenario.pack(side="left")
        boton(ctrl, "Generar caso", self.generar, width=130).pack(side="left", padx=(12, 0))
        boton(ctrl, "Clasificar texto editado", self.clasificar_editado, principal=False, width=180).pack(
            side="left", padx=(8, 0))
        self.btn_agregar = boton(ctrl, "Agregar a la suite", self.agregar, principal=False, width=150)
        self.btn_agregar.pack(side="right")
        self.txt_gen = ctk.CTkTextbox(cuerpo, height=60, font=(CUERPO, 13), wrap="word", fg_color=CAMPO,
                                      corner_radius=3, border_width=0, text_color=TEXTO)
        self.txt_gen.pack(fill="x", pady=(12, 10))
        res = ctk.CTkFrame(cuerpo, fg_color="transparent")
        res.pack(fill="x")
        self.campos_gen = {}
        for i, (k, lbl) in enumerate([("esp", "Esperado"), ("ia", "Resultado de la IA"), ("pal", "Palabras que pesaron"),
                                      ("ver", "Veredicto")]):
            c = ctk.CTkFrame(res, fg_color="transparent")
            c.grid(row=0, column=i, sticky="nw")
            res.grid_columnconfigure(i, weight=1, uniform="r")
            rotulo(c, lbl, size=9).pack(anchor="w")
            self.campos_gen[k] = ctk.CTkLabel(c, text="—", font=(CUERPO_SB, 12), text_color=TEXTO, anchor="w",
                                              justify="left", wraplength=320)
            self.campos_gen[k].pack(anchor="w")
        self.caso_actual = None

        # Suite
        ps = panel(self)
        ps.pack(fill="x", padx=32, pady=(0, 30))
        f = titulo_panel(ps, "Suite de casos de prueba")
        self.lbl_suite = ctk.CTkLabel(f, text="", font=(CUERPO_SB, 11), text_color=TEXTO_2)
        self.lbl_suite.pack(side="right")
        marco = ctk.CTkFrame(ps, fg_color="transparent")
        marco.pack(fill="x", padx=20, pady=(12, 18))
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in self.COLS], show="headings", height=14)
        for c, tt, w in self.COLS:
            izq = c in ("mensaje", "esp", "obt", "tipo")
            self.tabla.heading(c, text=tt, anchor="w" if izq else "center")
            self.tabla.column(c, width=w, anchor="w" if izq else "center", stretch=c == "mensaje")
        self.tabla.tag_configure("ok", background=BLANCO)
        self.tabla.tag_configure("falla", background=TINTE_ALTA)
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla.pack(fill="x")
        self.ejecutar()

    def casos_suite(self):
        base = [{"id": i, "tipo": t, "mensaje": m, "sentimiento": s, "tema": tm} for i, t, m, s, tm in SUITE]
        return base + self.extra

    def ejecutar(self):
        self.resultados = evaluar_casos(self.d, self.casos_suite())
        r = self.resultados
        self.tabla.delete(*self.tabla.get_children())
        for k, x in r.iterrows():
            self.tabla.insert("", "end", iid=str(k), tags=("ok" if x.ok else "falla",), values=(
                x["id"], x.tipo, x.mensaje, f"{x.sentimiento} · {x.tema}", f"{x.sent_ia} · {x.tema_ia}",
                pct(x.confianza, 0), "✓ Pasa" if x.ok else "✗ Falla"))
        est = r[r.tipo == "Estándar"]
        self.kpi.set("suite", f"{r.ok.sum()}/{len(r)}", f"estándar {est.ok.sum()}/{len(est)} · límite "
                                                        f"{r[r.tipo == 'Límite'].ok.sum()}/{(r.tipo == 'Límite').sum()}")
        self.lbl_suite.configure(text=f"Ejecutada {dt.datetime.now():%H:%M:%S} · {r.ok.sum()} de {len(r)} pasan")
        rep = self.d.reporte
        fallas = r[~r.ok]
        a_pos = (fallas.sent_ia == "Positivo").sum()
        self.lbl_limites.configure(text=(
            f"• Neutro es la clase débil: precisión {pct(rep['Neutro']['precision'], 0)}. Los mensajes tibios ('ok', "
            "'nada demais') suelen salir positivos.\n"
            f"• {a_pos} de las {len(fallas)} fallas de la suite fueron clasificadas como positivas por error, "
            "incluido el sarcasmo.\n"
            "• Mejora propuesta: reentrenar con las reseñas corregidas por los agentes y sumar más ejemplos neutros."))

    def generar(self):
        esc = self.escenario.get()
        self.caso_actual = generar(None if esc == "Aleatorio" else esc)
        self.txt_gen.delete("1.0", "end")
        self.txt_gen.insert("1.0", self.caso_actual["mensaje"])
        self.evaluar_actual(contar=True)

    def clasificar_editado(self):
        texto = self.txt_gen.get("1.0", "end").strip()
        if not texto:
            return
        if self.caso_actual is None:
            self.caso_actual = {"escenario": "Manual", "mensaje": texto, "sentimiento": "—", "tema": "—"}
        self.caso_actual = {**self.caso_actual, "mensaje": texto}
        self.evaluar_actual(contar=False)

    def evaluar_actual(self, contar):
        r = evaluar_casos(self.d, [self.caso_actual]).iloc[0]
        manual = self.caso_actual["sentimiento"] == "—"
        self.campos_gen["esp"].configure(text="Sin esperado (texto libre)" if manual else
                                         f"{r.sentimiento} · {r.tema}\nEscenario: {r.escenario}")
        self.campos_gen["ia"].configure(text=f"{r.sent_ia} · {r.tema_ia}\nConfianza {pct(r.confianza, 0)}")
        self.campos_gen["pal"].configure(text=r.palabras or "—")
        if manual:
            self.campos_gen["ver"].configure(text="—", text_color=TEXTO)
        else:
            self.campos_gen["ver"].configure(text="✓ CORRECTO" if r.ok else ("✗ INCORRECTO" if not r.ok_sent else
                                                                             "✗ TEMA DISTINTO"),
                                             text_color=PETROLEO if r.ok else COBRE)
        if contar and not manual:
            self.n_gen += 1
            self.ok_gen += int(r.ok)
            self.kpi.set("gen", f"{self.ok_gen}/{self.n_gen}", f"{pct(self.ok_gen / self.n_gen, 0)} correctos en esta "
                                                               "sesión")

    def agregar(self):
        if not self.caso_actual or self.caso_actual["sentimiento"] == "—":
            return
        n = len(self.extra) + 1
        self.extra.append({"id": f"G{n:02d}", "tipo": "Generado", "mensaje": self.caso_actual["mensaje"],
                           "sentimiento": self.caso_actual["sentimiento"], "tema": self.caso_actual["tema"]})
        self.ejecutar()
        self.tabla.see(self.tabla.get_children()[-1])

    def exportar(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile=f"pruebas_modelo_{dt.date.today()}.xlsx")
        if ruta:
            self.resultados.to_excel(ruta, index=False)
            messagebox.showinfo(APP_NOMBRE, f"Resultados guardados en:\n{ruta}")


# ---------------------------------------------------------------- Canales e integraciones
class PaginaCanales(ctk.CTkScrollableFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color=BLANCO, corner_radius=10)
        self.app = app
        encabezado(self, "Canales e integraciones", f"{ESPACIO}  ·  avisos, respuestas y coordinación")

        self.resumen = ctk.CTkLabel(self, text="", font=(CUERPO_SB, 12), text_color=TEXTO_2, anchor="w")
        self.resumen.pack(fill="x", padx=36, pady=(0, 8))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=26)
        self.switches, self.estados = {}, {}
        for i, c in enumerate(CANALES):
            card = panel(grid)
            card.grid(row=i // 4, column=i % 4, sticky="nsew", padx=6, pady=6)
            grid.grid_columnconfigure(i % 4, weight=1, uniform="g")
            cab = ctk.CTkFrame(card, fg_color="transparent")
            cab.pack(fill="x", padx=18, pady=(16, 0))
            inicial = ctk.CTkLabel(cab, text=c["nombre"][0], font=(DISPLAY_SB, 18), width=38, height=38,
                                   corner_radius=4, fg_color=TINTA, text_color="white")
            inicial.pack(side="left")
            sw = ctk.CTkButton(cab, text="", width=104, height=30, corner_radius=15, border_width=1,
                               font=(CUERPO_SB, 11), command=lambda cid=c["id"]: self.cambiar(cid))
            sw.pack(side="right")
            self.switches[c["id"]] = sw
            ctk.CTkLabel(card, text=c["nombre"], font=(DISPLAY_SB, 16), text_color=TINTA, anchor="w").pack(
                fill="x", padx=18, pady=(12, 0))
            meta = ctk.CTkFrame(card, fg_color="transparent")
            meta.pack(fill="x", padx=18)
            rotulo(meta, c["publico"], size=9).pack(side="left")
            self.estados[c["id"]] = ctk.CTkLabel(meta, text="", font=(CUERPO_SB, 10))
            self.estados[c["id"]].pack(side="right")
            ctk.CTkLabel(card, text=c["hace"], font=(CUERPO, 12), text_color=TEXTO, anchor="w", justify="left",
                         wraplength=280).pack(fill="x", padx=18, pady=(8, 8))
            if c["id"] == "telegram":
                fila_tg = ctk.CTkFrame(card, fg_color="transparent")
                fila_tg.pack(fill="x", padx=18, pady=(0, 8))
                self.lbl_tg = ctk.CTkLabel(fila_tg, text="", font=(CUERPO_SB, 11), text_color=TEXTO_2, anchor="w")
                self.lbl_tg.pack(side="left")
                ctk.CTkButton(fila_tg, text="Configurar bot  →", command=app.dialogo_telegram, width=120, height=24,
                              fg_color="transparent", hover_color="#F1EEE6", text_color=TINTA,
                              font=(CUERPO_SB, 11)).pack(side="right")
            linea(card, padx=18)
            rotulo(card, "Por qué", PETROLEO, 9).pack(fill="x", padx=18, pady=(8, 0))
            ctk.CTkLabel(card, text=app.datos.por_que[c["id"]], font=(CUERPO, 11), text_color=TEXTO_2, anchor="w",
                         justify="left", wraplength=280).pack(fill="x", padx=18, pady=(0, 16))

        pr = panel(self)
        pr.pack(fill="x", padx=32, pady=(14, 30))
        titulo_panel(pr, "Reglas de automatización")
        marco = ctk.CTkFrame(pr, fg_color="transparent")
        marco.pack(fill="x", padx=20, pady=(12, 18))
        cols = [("cuando", "Cuando…", 380), ("entonces", "Entonces…", 300), ("canal", "Canal", 170),
                ("plazo", "Plazo", 100), ("estado", "Estado", 110)]
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in cols], show="headings", height=len(REGLAS))
        for c, t, w in cols:
            self.tabla.heading(c, text=t, anchor="w")
            self.tabla.column(c, width=w, anchor="w", stretch=c in ("cuando", "entonces"))
        self.tabla.tag_configure("activa", background=BLANCO, foreground=TEXTO)
        self.tabla.tag_configure("pausada", background="#F4F1EA", foreground="#A39E92")
        self.tabla.pack(fill="x")
        self.refrescar()

    def cambiar(self, cid):
        if cid == "telegram":
            conf = self.app.telegram
            if not telegram_bot.configurado(conf):
                self.app.dialogo_telegram()
                return
            conf["activo"] = not self.app.canales["telegram"]
            telegram_bot.guardar(conf)
        self.app.canales[cid] = not self.app.canales[cid]
        self.refrescar()
        self.app.canales_actualizados()

    def refrescar(self):
        nombres = {c["id"]: c["nombre"] for c in CANALES}
        activos = sum(self.app.canales.values())
        for c in CANALES:
            on = self.app.canales[c["id"]]
            self.estados[c["id"]].configure(text="● ACTIVO" if on else "○ INACTIVO",
                                            text_color=PETROLEO if on else TEXTO_2)
            if c["id"] == "telegram" and not telegram_bot.configurado(self.app.telegram):
                self.switches[c["id"]].configure(text="Configurar", fg_color="transparent", hover_color="#EFEBE1",
                                                 border_color=COBRE, text_color=COBRE)
            elif on:
                self.switches[c["id"]].configure(text="✓  Conectado", fg_color=PETROLEO, hover_color="#24554F",
                                                 border_color=PETROLEO, text_color="white")
            else:
                self.switches[c["id"]].configure(text="Conectar", fg_color="transparent", hover_color="#EFEBE1",
                                                 border_color=TINTA, text_color=TINTA)
        self.tabla.delete(*self.tabla.get_children())
        n_act = 0
        for cuando, entonces, canal, plazo in REGLAS:
            on = self.app.canales[canal]
            n_act += on
            self.tabla.insert("", "end", values=(cuando, entonces, nombres[canal], plazo,
                                                 "● Activa" if on else "Pausada"), tags=("activa" if on else
                                                                                          "pausada",))
        self.resumen.configure(text=f"{activos} de {len(CANALES)} canales activos  ·  {n_act} de {len(REGLAS)} reglas "
                                    "en funcionamiento")
        tg = self.app.telegram
        self.lbl_tg.configure(text=(f"@{tg.get('bot', '')} → {tg.get('chat_nombre', '')}" if
                                    telegram_bot.configurado(tg) else "Sin configurar"))


# ---------------------------------------------------------------- ventana principal
ICONOS = {"inicio": "\uE80F", "analisis": "\uE9D2", "ia": "\uE715", "voz": "\uE90A", "modelo": "\uE99A",
          "canales": "\uE71B"}
ICONOS_FUENTE = "Segoe MDL2 Assets"


class ItemMenu(ctk.CTkFrame):
    """Ícono de la barra lateral angosta, con el nombre del módulo al pasar el mouse."""

    def __init__(self, padre, app, icono, texto, comando):
        super().__init__(padre, fg_color=TINTA, corner_radius=0, height=52)
        self.app, self.texto = app, texto
        self.indicador = ctk.CTkFrame(self, width=3, height=1, fg_color=TINTA, corner_radius=0)
        self.indicador.pack(side="left", fill="y")
        self.boton = ctk.CTkButton(self, text=icono, width=58, height=48, corner_radius=8, font=(ICONOS_FUENTE, 19),
                                   fg_color="transparent", hover_color=TINTA_2, text_color="#8FA3B8", command=comando)
        self.boton.pack(side="left", padx=(5, 6), pady=2)
        self.badge = ctk.CTkLabel(self, text="", font=(CUERPO_SB, 9), fg_color=COBRE, text_color="white",
                                  corner_radius=8, width=18, height=16)
        self.boton.bind("<Enter>", self._mostrar, add="+")
        self.boton.bind("<Leave>", lambda e: app.ocultar_tip(), add="+")

    def _mostrar(self, _):
        y = self.winfo_rooty() - self.app.winfo_rooty() + self.winfo_height() // 2
        self.app.mostrar_tip(self.texto, y)

    def set_badge(self, n):
        if n:
            self.badge.configure(text=str(n))
            self.badge.place(x=44, y=6)
            self.badge.lift()
        else:
            self.badge.place_forget()

    def activar(self, activo):
        self.indicador.configure(fg_color=COBRE if activo else TINTA)
        self.boton.configure(fg_color=TINTA_2 if activo else "transparent",
                             text_color="white" if activo else "#8FA3B8")


class App(ctk.CTk):
    TITULOS = {"inicio": "Inicio", "analisis": "Analítica", "ia": "Bandeja IA", "voz": "Voz del cliente",
               "modelo": "Modelo IA",
               "canales": "Canales"}

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"{APP_NOMBRE} · Centro de Operaciones Digitales")
        self.geometry("1440x900")
        self.minsize(1240, 760)
        self.configure(fg_color=PAPEL)
        self.canales = {c["id"]: c["activo"] for c in CANALES}
        self.telegram = telegram_bot.cargar()   # token y chat guardados solo en este PC
        self.canales["telegram"] = telegram_bot.configurado(self.telegram) and self.telegram.get("activo", True)
        self.paginas, self.items = {}, {}
        try:
            self.iconbitmap(recurso("icono.ico"))
        except Exception:
            pass
        try:
            self.after(0, lambda: self.state("zoomed"))
        except Exception:
            pass

        self.lateral = ctk.CTkFrame(self, width=72, corner_radius=0, fg_color=TINTA)
        self.lateral.pack(side="left", fill="y")
        self.lateral.pack_propagate(False)
        derecha = ctk.CTkFrame(self, fg_color=PAPEL, corner_radius=0)
        derecha.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(self.lateral, text="P", font=(DISPLAY_SB, 20), width=38, height=38, corner_radius=8,
                     fg_color=COBRE, text_color="white").pack(pady=(20, 22))
        self.menu_op = ctk.CTkFrame(self.lateral, fg_color="transparent")
        self.menu_op.pack(fill="x")
        ctk.CTkFrame(self.lateral, height=1, fg_color="#22405C", corner_radius=0).pack(fill="x", padx=18, pady=12)
        self.menu_cfg = ctk.CTkFrame(self.lateral, fg_color="transparent")
        self.menu_cfg.pack(fill="x")

        pie = ctk.CTkFrame(self.lateral, fg_color="transparent")
        pie.pack(side="bottom", fill="x", pady=(0, 40))
        self.btn_buscar = ctk.CTkButton(pie, text="\uE895", width=44, height=40, corner_radius=8,
                                        font=(ICONOS_FUENTE, 15), fg_color="transparent", hover_color=TINTA_2,
                                        text_color="#8FA3B8", command=lambda: self.buscar_actualizacion(True))
        self.btn_buscar.pack()
        self.btn_buscar.bind("<Enter>", lambda e: self.mostrar_tip(
            "Buscar actualizaciones", self.btn_buscar.winfo_rooty() - self.winfo_rooty() + 20), add="+")
        self.btn_buscar.bind("<Leave>", lambda e: self.ocultar_tip(), add="+")
        ctk.CTkLabel(pie, text=f"v{VERSION}", font=(CUERPO, 10), text_color="#5F7590").pack(pady=(2, 0))
        self.tip = ctk.CTkLabel(self, text="", font=(CUERPO_SB, 12), fg_color=TINTA_2, text_color="white",
                                corner_radius=6, height=30)

        # Aviso de versión nueva (oculto hasta que el actualizador encuentre una)
        self.aviso = ctk.CTkFrame(derecha, fg_color="#FBEDE7", corner_radius=0, height=44)
        self.aviso.pack_propagate(False)
        self.lbl_aviso = ctk.CTkLabel(self.aviso, text="", font=(CUERPO_SB, 12), text_color=TINTA)
        self.lbl_aviso.pack(side="left", padx=(32, 12))
        ctk.CTkButton(self.aviso, text="Más tarde", width=90, height=28, fg_color="transparent",
                      hover_color="#F3DCD2", text_color=TEXTO_2, font=(CUERPO_SB, 11),
                      command=lambda: self.aviso.pack_forget()).pack(side="right", padx=(6, 32))
        boton(self.aviso, "Actualizar", lambda: self.dialogo_actualizacion(), width=110, height=28).pack(side="right")
        self.nueva_version = None

        self.contenido = ctk.CTkFrame(derecha, fg_color=PAPEL, corner_radius=0)
        self.contenido.pack(fill="both", expand=True)
        self.cargando = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self.cargando.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(self.cargando, text="PULSO", font=(DISPLAY_SB, 40), text_color=TINTA).pack()
        ctk.CTkLabel(self.cargando, text="Sincronizando pedidos y cargando el modelo de IA…", font=(CUERPO, 13),
                     text_color=TEXTO_2).pack(pady=(4, 12))
        barra = ctk.CTkProgressBar(self.cargando, width=260, height=4, mode="indeterminate", progress_color=COBRE,
                                   fg_color=LINEA)
        barra.pack()
        barra.start()
        self.after(200, self.iniciar)

    def iniciar(self):
        try:
            self.datos = Datos()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_NOMBRE, f"No se pudieron cargar los datos:\n{e}")
            self.destroy()
            return
        estilo_tablas()
        self.cargando.destroy()
        # La bandeja se crea primero para que Inicio muestre sus alertas
        self.paginas["ia"] = PaginaIA(self.contenido, self)
        self.paginas["inicio"] = PaginaInicio(self.contenido, self)
        self.paginas["analisis"] = PaginaAnalisis(self.contenido, self)
        self.paginas["voz"] = PaginaVoz(self.contenido, self)
        self.paginas["modelo"] = PaginaModelo(self.contenido, self)
        self.paginas["canales"] = PaginaCanales(self.contenido, self)
        for clave, grupo in (("inicio", self.menu_op), ("analisis", self.menu_op), ("ia", self.menu_op),
                             ("voz", self.menu_op), ("modelo", self.menu_cfg), ("canales", self.menu_cfg)):
            item = ItemMenu(grupo, self, ICONOS[clave], self.TITULOS[clave], lambda c=clave: self.ir(c))
            item.pack(fill="x")
            self.items[clave] = item
        self.paginas["ia"].procesar(avisar=False)   # lote inicial de muestra: no envía avisos
        inicial = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in self.paginas else "inicio"
        self.ir(inicial)
        self.after(1500, lambda: self.buscar_actualizacion(False))
        self.after(15000, self._vigilar)

    def mostrar_tip(self, texto, y):
        self.tip.configure(text=f"   {texto}   ")
        self.tip.place(x=78, y=y, anchor="w")
        self.tip.lift()

    def ocultar_tip(self):
        self.tip.place_forget()

    # --- Telegram: configuración del bot y envío de avisos
    def dialogo_telegram(self):
        conf = dict(self.telegram)
        dlg = ctk.CTkToplevel(self)
        dlg.title("Configurar Telegram")
        dlg.geometry("600x620")
        dlg.resizable(False, False)
        dlg.configure(fg_color=BLANCO)
        dlg.transient(self)
        dlg.after(100, dlg.grab_set)
        ctk.CTkLabel(dlg, text="Avisos por Telegram", font=(DISPLAY_SB, 24), text_color=TINTA, anchor="w").pack(
            fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(dlg, text="PULSO te escribe al celular cada vez que entra un ticket crítico.", font=(CUERPO, 12),
                     text_color=TEXTO_2, anchor="w").pack(fill="x", padx=28, pady=(0, 10))

        def paso(n, titulo, texto):
            f = ctk.CTkFrame(dlg, fg_color="transparent")
            f.pack(fill="x", padx=28, pady=(12, 0))
            ctk.CTkLabel(f, text=f"{n}", font=(DISPLAY_SB, 22), text_color=COBRE, width=28, anchor="nw").pack(
                side="left", anchor="n")
            cuerpo = ctk.CTkFrame(f, fg_color="transparent")
            cuerpo.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(cuerpo, text=titulo, font=(CUERPO_SB, 13), text_color=TEXTO, anchor="w").pack(fill="x")
            ctk.CTkLabel(cuerpo, text=texto, font=(CUERPO, 12), text_color=TEXTO_2, anchor="w", justify="left",
                         wraplength=500).pack(fill="x")
            return cuerpo

        c1 = paso(1, "Crea el bot y pega su token",
                  "En Telegram, escribe a @BotFather, envía /newbot y sigue las instrucciones. Te dará un token.")
        fila1 = ctk.CTkFrame(c1, fg_color="transparent")
        fila1.pack(fill="x", pady=(6, 0))
        token = ctk.CTkEntry(fila1, show="•", placeholder_text="123456789:AA…", corner_radius=3, height=32,
                             border_color=LINEA, fg_color=CAMPO, font=(CUERPO, 12))
        token.pack(side="left", fill="x", expand=True)
        if conf.get("token"):
            token.insert(0, conf["token"])
        b_ver = boton(fila1, "Verificar", lambda: verificar(), principal=False, width=90, height=32)
        b_ver.pack(side="left", padx=(8, 0))
        r1 = ctk.CTkLabel(c1, text=f"✓ Bot @{conf['bot']}" if conf.get("bot") else "", font=(CUERPO_SB, 11),
                          text_color=PETROLEO, anchor="w")
        r1.pack(fill="x")

        c2 = paso(2, "Escríbele a tu bot",
                  "Busca tu bot en Telegram (en el celular o en Telegram Web) y aprieta «Iniciar». Después aprieta "
                  "«Detectar chat».")
        fila2 = ctk.CTkFrame(c2, fg_color="transparent")
        fila2.pack(fill="x", pady=(6, 0))
        boton(fila2, "Abrir en la app", lambda: conf.get("bot") and webbrowser.open(f"https://t.me/{conf['bot']}"),
              principal=False, width=120, height=32).pack(side="left")
        boton(fila2, "Telegram Web", lambda: conf.get("bot") and webbrowser.open(
            f"https://web.telegram.org/k/#@{conf['bot']}"), principal=False, width=120, height=32).pack(
            side="left", padx=(8, 0))
        boton(fila2, "Detectar chat", lambda: detectar(), principal=False, width=120, height=32).pack(
            side="left", padx=(8, 0))
        r2 = ctk.CTkLabel(c2, text=f"✓ Chat: {conf['chat_nombre']}" if conf.get("chat_id") else "",
                          font=(CUERPO_SB, 11), text_color=PETROLEO, anchor="w")
        r2.pack(fill="x")

        c3 = paso(3, "Prueba el aviso", "Envía un mensaje de prueba para confirmar que llega a tu celular.")
        b_prueba = boton(c3, "Enviar mensaje de prueba", lambda: probar(), principal=False, width=190, height=32)
        b_prueba.pack(anchor="w", pady=(6, 0))
        r3 = ctk.CTkLabel(c3, text="", font=(CUERPO_SB, 11), text_color=PETROLEO, anchor="w")
        r3.pack(fill="x")

        estado = ctk.CTkLabel(dlg, text="El token se guarda solo en este computador.", font=(CUERPO, 11),
                              text_color=TEXTO_2, anchor="w")
        botones = ctk.CTkFrame(dlg, fg_color="transparent")
        botones.pack(side="bottom", fill="x", padx=28, pady=18)
        estado.pack(side="bottom", fill="x", padx=28)
        boton(botones, "Cancelar", dlg.destroy, principal=False, width=100).pack(side="right", padx=(8, 0))
        boton(botones, "Guardar", lambda: guardar(), width=110).pack(side="right")
        if telegram_bot.configurado(conf):
            ctk.CTkButton(botones, text="Desconectar", command=lambda: desconectar(), fg_color="transparent",
                          hover_color="#F5E4DD", text_color=COBRE, font=(CUERPO_SB, 12), width=100).pack(side="left")

        def en_hilo(fn, ok, etiqueta):
            def tarea():
                try:
                    res = fn()
                except telegram_bot.ErrorTelegram as e:
                    msg = str(e)
                    self.after(0, lambda: etiqueta.configure(text=msg, text_color=COBRE))
                    return
                self.after(0, lambda: ok(res))
            threading.Thread(target=tarea, daemon=True).start()

        def verificar():
            conf["token"] = token.get().strip()
            r1.configure(text="Verificando…", text_color=TEXTO_2)

            def ok(bot):
                conf["bot"] = bot
                r1.configure(text=f"✓ Bot @{bot}", text_color=PETROLEO)
            en_hilo(lambda: telegram_bot.verificar_token(conf["token"]), ok, r1)

        def detectar():
            if not conf.get("bot"):
                r2.configure(text="Primero verifica el token (paso 1).", text_color=COBRE)
                return
            r2.configure(text="Buscando tu mensaje…", text_color=TEXTO_2)

            def ok(res):
                if not res:
                    r2.configure(text="No hay mensajes: envía /start al bot y vuelve a intentar.", text_color=COBRE)
                    return
                conf["chat_id"], conf["chat_nombre"] = res
                r2.configure(text=f"✓ Chat: {res[1]}", text_color=PETROLEO)
            en_hilo(lambda: telegram_bot.detectar_chat(conf["token"]), ok, r2)

        def probar():
            if not telegram_bot.configurado(conf):
                r3.configure(text="Completa los pasos 1 y 2.", text_color=COBRE)
                return
            r3.configure(text="Enviando…", text_color=TEXTO_2)
            en_hilo(lambda: telegram_bot.enviar(conf["token"], conf["chat_id"],
                                                "✅ <b>PULSO conectado.</b>\nDesde ahora te aviso aquí cada ticket "
                                                "crítico de la Bandeja IA."),
                    lambda _: r3.configure(text="✓ Mensaje enviado: revisa Telegram.", text_color=PETROLEO), r3)

        def guardar():
            if not telegram_bot.configurado(conf):
                estado.configure(text="Completa los pasos 1 y 2 antes de guardar.", text_color=COBRE)
                return
            conf["activo"] = True
            telegram_bot.guardar(conf)
            self.telegram = conf
            self.canales["telegram"] = True
            self.paginas["canales"].refrescar()
            dlg.destroy()

        def desconectar():
            telegram_bot.guardar({})
            self.telegram = {}
            self.canales["telegram"] = False
            self.paginas["canales"].refrescar()
            dlg.destroy()

    def enviar_telegram(self, texto, etiqueta=None):
        """Envía un mensaje a Telegram en segundo plano; si no está configurado, ofrece configurarlo."""
        if not telegram_bot.configurado(self.telegram):
            if messagebox.askyesno(APP_NOMBRE, "Telegram no está configurado. ¿Quieres configurarlo ahora?"):
                self.dialogo_telegram()
            return
        if etiqueta is not None:
            etiqueta.configure(text="Enviando a Telegram…", text_color=TEXTO_2)
        conf = dict(self.telegram)

        def tarea():
            try:
                telegram_bot.enviar(conf["token"], conf["chat_id"], texto)
                res = ("✓ Enviado a Telegram", PETROLEO)
            except telegram_bot.ErrorTelegram as e:
                res = (str(e), COBRE)
            if etiqueta is not None:
                self.after(0, lambda: etiqueta.configure(text=res[0], text_color=res[1]))

        threading.Thread(target=tarea, daemon=True).start()

    MINUTOS_AVISO = 30   # recordar un urgente sin aprobar cuando falta media hora para su plazo

    def _vigilar(self):
        """Cada minuto: recuerda por Telegram los urgentes sin aprobar que están por vencer (si el canal está activo)."""
        try:
            ia = self.paginas.get("ia")
            if ia is not None and self.canales.get("telegram") and telegram_bot.configurado(self.telegram):
                ahora = dt.datetime.now()
                for i, r in ia.pendientes_alta().iterrows():
                    falta = int((r.limite - ahora).total_seconds() // 60)
                    if i not in ia.avisados_vencer and falta <= self.MINUTOS_AVISO:
                        ia.avisados_vencer.add(i)
                        self.enviar_telegram(telegram_bot.mensaje_por_vencer(r.to_dict(), falta), ia.lbl_tg)
        finally:
            self.after(60000, self._vigilar)

    def avisar_telegram(self, tickets, al_terminar=None):
        """Envía en segundo plano los tickets críticos a Telegram, si el canal está activo."""
        if not (self.canales.get("telegram") and telegram_bot.configurado(self.telegram)):
            return
        conf = dict(self.telegram)

        def tarea():
            try:
                n, error = telegram_bot.avisar_criticos(conf, tickets), None
            except telegram_bot.ErrorTelegram as e:
                n, error = 0, str(e)
            if al_terminar:
                self.after(0, lambda: al_terminar(n, error))

        threading.Thread(target=tarea, daemon=True).start()

    # --- actualización automática desde GitHub
    def buscar_actualizacion(self, manual):
        if manual:
            self.btn_buscar.configure(state="disabled")

        def tarea():
            try:
                info, error = actualizador.buscar(VERSION), None
            except Exception as e:  # noqa: BLE001  (sin internet, GitHub caído, etc.)
                info, error = None, e
            self.after(0, lambda: self._resultado_busqueda(info, error, manual))

        threading.Thread(target=tarea, daemon=True).start()

    def _resultado_busqueda(self, info, error, manual):
        self.btn_buscar.configure(state="normal")
        if info:
            self.nueva_version = info
            self.lbl_aviso.configure(text=f"PULSO {info['version']} está disponible  ·  tienes la {VERSION}")
            self.aviso.pack(fill="x", before=self.contenido)
            if manual:
                self.dialogo_actualizacion()
        elif manual:
            if error:
                messagebox.showwarning(APP_NOMBRE, "No se pudo consultar GitHub. Revisa tu conexión a internet.")
            else:
                messagebox.showinfo(APP_NOMBRE, f"Tienes la última versión (PULSO {VERSION}).")

    def dialogo_actualizacion(self):
        info = self.nueva_version
        if not info:
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Actualizar PULSO")
        dlg.geometry("560x470")
        dlg.resizable(False, False)
        dlg.configure(fg_color=BLANCO)
        dlg.transient(self)
        dlg.after(100, dlg.grab_set)
        try:
            dlg.after(250, lambda: dlg.iconbitmap(recurso("icono.ico")))
        except Exception:
            pass
        ctk.CTkLabel(dlg, text=f"PULSO {info['version']}", font=(DISPLAY_SB, 26), text_color=TINTA,
                     anchor="w").pack(fill="x", padx=28, pady=(24, 0))
        ctk.CTkLabel(dlg, text=f"Versión instalada: {VERSION}", font=(CUERPO, 12), text_color=TEXTO_2,
                     anchor="w").pack(fill="x", padx=28)
        rotulo(dlg, "Novedades").pack(fill="x", padx=28, pady=(16, 4))
        notas = ctk.CTkTextbox(dlg, height=190, font=(CUERPO, 12), wrap="word", fg_color=CAMPO, corner_radius=3,
                               border_width=0, text_color=TEXTO)
        notas.pack(fill="x", padx=28)
        notas.insert("1.0", info["notas"].replace("**", "").replace("`", "") or "Sin notas.")
        notas.configure(state="disabled")
        barra = ctk.CTkProgressBar(dlg, height=6, corner_radius=3, progress_color=COBRE, fg_color=LINEA)
        barra.set(0)
        estado = ctk.CTkLabel(dlg, text="", font=(CUERPO, 11), text_color=TEXTO_2, anchor="w")
        botones = ctk.CTkFrame(dlg, fg_color="transparent")
        botones.pack(side="bottom", fill="x", padx=28, pady=20)
        estado.pack(side="bottom", fill="x", padx=28)
        barra.pack(side="bottom", fill="x", padx=28, pady=(0, 6))
        cancelar = {"v": False}

        def cerrar():
            cancelar["v"] = True
            dlg.destroy()

        boton(botones, "Más tarde", cerrar, principal=False, width=110).pack(side="right", padx=(8, 0))
        if actualizador.es_instalado() and info["instalador"]:
            btn = boton(botones, "Actualizar ahora", lambda: empezar(), width=150)
        else:
            # Portable o código fuente: no se puede reemplazar a sí mismo, se abre la página de descarga
            btn = boton(botones, "Ir a la descarga", lambda: (webbrowser.open(info["pagina"]), cerrar()), width=150)
            estado.configure(text="La versión portable se actualiza descargando el archivo nuevo desde GitHub.")
        btn.pack(side="right")
        dlg.protocol("WM_DELETE_WINDOW", cerrar)

        def empezar():
            btn.configure(state="disabled", text="Descargando…")
            mb = info["instalador"]["tamano"] / 1048576

            def progreso(leido, total):
                self.after(0, lambda: (barra.set(leido / total),
                                       estado.configure(text=f"{num(leido / 1048576, 1)} de {num(mb, 1)} MB")))

            def tarea():
                try:
                    ruta = actualizador.descargar(info["instalador"], progreso, lambda: cancelar["v"])
                except InterruptedError:
                    return
                except Exception as e:  # noqa: BLE001
                    self.after(0, lambda: (estado.configure(text=str(e), text_color=COBRE),
                                           btn.configure(state="normal", text="Reintentar")))
                    return
                self.after(0, lambda: instalar(ruta))

            threading.Thread(target=tarea, daemon=True).start()

        def instalar(ruta):
            estado.configure(text="Huella SHA-256 verificada. Instalando; PULSO se volverá a abrir solo.",
                             text_color=PETROLEO)
            dlg.update()
            actualizador.instalar(ruta)
            self.after(800, self.destroy)

    def ir(self, clave, procesar=False, exportar=False, region=None, categoria=None, urgentes=False):
        for c, p in self.paginas.items():
            p.pack_forget()
        for c, it in self.items.items():
            it.activar(c == clave)
        self.paginas[clave].pack(fill="both", expand=True, padx=14, pady=14)
        if procesar:
            self.paginas["ia"].procesar()
        if urgentes:
            self.paginas["ia"].ver_urgentes()
        if region or categoria:
            self.paginas["analisis"].aplicar(region, categoria)
        if exportar:
            self.paginas["analisis"].exportar()

    def bandeja_actualizada(self, alta):
        if "ia" in self.items:
            self.items["ia"].set_badge(alta)
        if "inicio" in self.paginas:
            self.paginas["inicio"].pintar_alertas()

    def canales_actualizados(self):
        ia = self.paginas["ia"]
        if not ia.resultados.empty:   # re-clasifica la bandeja actual con los canales vigentes
            res = ia.clasificar(ia.resultados.mensaje.tolist())
            for col in ("nota_real", "sentimiento_real", "fecha_resena") + PaginaIA.ESTADO:
                res[col] = ia.resultados[col].values
            ia.resultados = res
            ia.refrescar()


if __name__ == "__main__":
    App().mainloop()
