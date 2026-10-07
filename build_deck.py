"""
Llena la plantilla INACAP de la Evaluación N°2 con el caso PULSO / Olist Store.
Entrada:  ppt/plantilla.pptx, ppt/img/app_*.png (capturas de la app)
Salida:   ppt/Evaluacion2_PULSO_Olist.pptx
"""
import copy

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

ROJO = RGBColor(0xE1, 0x20, 0x1C)
GRIS = RGBColor(0x58, 0x58, 0x5A)
TEXTO = RGBColor(0x53, 0x53, 0x53)
SUAVE = RGBColor(0x8A, 0x8A, 0x8C)
LINEA = RGBColor(0xD9, 0xD9, 0xD9)
FONDO = RGBColor(0xF3, 0xF3, 0xF3)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
VERDE = RGBColor(0x2E, 0x6B, 0x66)
FUENTE = "Open Sans"
FUENTE_L = "Open Sans Light"

X0, X1 = 101, 1819          # márgenes izquierdo / derecho del contenido (pt)
Y0, YMAX = 230, 960         # bajo el título / sobre el pie con logo
ANCHO = X1 - X0

prs = Presentation("ppt/plantilla.pptx")
LAYOUT_CONTENIDO = next(l for l in prs.slide_layouts if l.name == "1_Contenido")


# ---------------------------------------------------------------- utilidades
def texto(slide, x, y, w, h, contenido, size=28, color=TEXTO, bold=False, align=PP_ALIGN.LEFT,
          font=FUENTE, anchor=MSO_ANCHOR.TOP, espacio=0, nombre=None):
    """contenido: str, o lista de párrafos; cada párrafo es str o lista de (texto, {opciones})."""
    tb = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
    if nombre:
        tb.name = nombre
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    parrafos = contenido if isinstance(contenido, list) else [contenido]
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if espacio and i:
            p.space_before = Pt(espacio)
        runs = par if isinstance(par, list) else [(par, {})]
        for t, op in runs:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = op.get("font", font)
            f.size = Pt(op.get("size", size))
            f.bold = op.get("bold", bold)
            f.italic = op.get("italic", False)
            f.color.rgb = op.get("color", color)
    return tb


def caja(slide, x, y, w, h, relleno=FONDO, borde=None, forma=MSO_SHAPE.RECTANGLE, nombre=None):
    s = slide.shapes.add_shape(forma, Pt(x), Pt(y), Pt(w), Pt(h))
    if nombre:
        s.name = nombre
    if relleno is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = relleno
    if borde is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = borde
        s.line.width = Pt(1.5)
    s.shadow.inherit = False
    if forma == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def texto_en(s, contenido, size=24, color=TEXTO, bold=False, align=PP_ALIGN.CENTER, margen=14):
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Pt(margen)
    tf.margin_top = tf.margin_bottom = Pt(6)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    parrafos = contenido if isinstance(contenido, list) else [contenido]
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = par if isinstance(par, list) else [(par, {})]
        for t, op in runs:
            r = p.add_run()
            r.text = t
            r.font.name = op.get("font", FUENTE)
            r.font.size = Pt(op.get("size", size))
            r.font.bold = op.get("bold", bold)
            r.font.color.rgb = op.get("color", color)


def imagen(slide, ruta, x, y, w=None, h=None, recorte=None, nombre=None):
    """Inserta una captura (opcionalmente recortada) con un borde fino gris."""
    im = Image.open(ruta)
    if recorte:
        im = im.crop(recorte)
        ruta = ruta.replace(".png", f"_r{recorte[0]}_{recorte[1]}.png")
        im.save(ruta)
    ar = im.width / im.height
    if w and not h:
        h = w / ar
    elif h and not w:
        w = h * ar
    pic = slide.shapes.add_picture(ruta, Pt(x), Pt(y), Pt(w), Pt(h))
    pic.line.color.rgb = LINEA
    pic.line.width = Pt(1.5)
    if nombre:
        pic.name = nombre
    return pic, w, h


def flecha(slide, x1, y1, x2, y2, color=SUAVE):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(x1), Pt(y1), Pt(x2), Pt(y2))
    c.line.color.rgb = color
    c.line.width = Pt(2.5)
    ln = c.line._get_or_add_ln()
    ln.append(etree.SubElement(ln, qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def tabla(slide, x, y, w, filas, anchos, size=20, alto_fila=60, encabezado_color=GRIS, resaltar_col=None):
    nf, nc = len(filas), len(filas[0])
    gt = slide.shapes.add_table(nf, nc, Pt(x), Pt(y), Pt(w), Pt(alto_fila * nf))
    tbl = gt.table
    tbl.first_row = True
    total = sum(anchos)
    for j, a in enumerate(anchos):
        tbl.columns[j].width = Pt(w * a / total)
    for i, fila in enumerate(filas):
        tbl.rows[i].height = Pt(alto_fila)
        for j, val in enumerate(fila):
            cel = tbl.cell(i, j)
            cel.margin_left = cel.margin_right = Pt(12)
            cel.margin_top = cel.margin_bottom = Pt(8)
            cel.vertical_anchor = MSO_ANCHOR.MIDDLE
            cel.fill.solid()
            cel.fill.fore_color.rgb = encabezado_color if i == 0 else (FONDO if i % 2 == 0 else BLANCO)
            tf = cel.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = ""
            r = p.add_run()
            r.text = str(val)
            r.font.name = FUENTE
            r.font.size = Pt(size)
            r.font.bold = i == 0 or (resaltar_col is not None and j == resaltar_col)
            r.font.color.rgb = BLANCO if i == 0 else (ROJO if (resaltar_col == j) else TEXTO)
    # sin estilo de tabla por defecto (bandas azules de Office)
    tblPr = tbl._tbl.tblPr
    for attr in ("bandRow", "firstRow"):
        tblPr.set(attr, "0")
    return gt


def num_es(v):
    return f"{v:.1f}".replace(".", ",")


def notas(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


def poner_titulo(slide, titulo):
    ph = next(s for s in slide.placeholders if s.placeholder_format.idx == 13)
    tf = ph.text_frame
    p = tf.paragraphs[0]
    for r in list(p.runs)[1:]:
        r._r.getparent().remove(r._r)
    r = p.runs[0] if p.runs else p.add_run()
    r.text = titulo
    r.font.size = Pt(54)
    r.font.bold = True
    return ph


def nueva_diapositiva(despues_de, titulo):
    s = prs.slides.add_slide(LAYOUT_CONTENIDO)
    poner_titulo(s, titulo)
    lst = prs.slides._sldIdLst
    nuevo = lst[-1]
    lst.remove(nuevo)
    pos = [prs.slides.get(int(e.get("id"))) for e in lst].index(despues_de)
    lst.insert(pos + 1, nuevo)
    return s


def limpiar_vacios(slide):
    for sh in list(slide.shapes):
        if sh.shape_type == 17 and sh.has_text_frame and not sh.text_frame.text.strip():
            sh._element.getparent().remove(sh._element)


def etiqueta(slide, x, y, txt, color=ROJO):
    """Rótulo corto en mayúsculas (criterio de la pauta)."""
    return texto(slide, x, y, ANCHO, 30, txt.upper(), size=18, color=color, bold=True)


def numero(slide, x, y, n, size=44, color=ROJO):
    return texto(slide, x, y, 110, size * 1.3, f"{n:02d}", size=size, color=color, bold=True)


S = list(prs.slides)
portada, temario, intro, entorno, necesidades, seleccion, clave, implem, cambio, impacto, concl, biblio, cierre = S

# Diapositivas nuevas para el prototipo (después de "Tecnologías clave")
s_analisis = nueva_diapositiva(clave, "Análisis de datos para decidir")
s_ia = nueva_diapositiva(s_analisis, "Automatización de procesos con IA")
s_voz = nueva_diapositiva(s_ia, "Voz del cliente: la IA sobre todas las reseñas")
s_valid = nueva_diapositiva(s_voz, "Pruebas y validación del modelo")
s_canales = nueva_diapositiva(s_valid, "Plataformas y canales digitales")
s_integ = nueva_diapositiva(s_canales, "Integración en los procesos de la organización")
s_canales_app = nueva_diapositiva(s_integ, "Canales e integraciones en PULSO")

for s in prs.slides:
    limpiar_vacios(s)

# ---------------------------------------------------------------- 1. Portada
for sh in portada.shapes:
    if not sh.has_text_frame:
        continue
    t = sh.text_frame.text
    run = sh.text_frame.paragraphs[0].runs[0] if sh.text_frame.paragraphs[0].runs else None
    if run is None:
        continue
    if t == "Tecnologías":
        run.text = "PULSO: transformación digital de Olist Store"
    elif t == "Sub-título":
        run.text = "Datos, IA y canales digitales · Evaluación N°2"
notas(portada, "Presento PULSO, un centro de operaciones digitales que diseñé para Olist Store, un marketplace "
               "brasileño. Trabajé con datos reales de Kaggle: casi 100 mil pedidos. La propuesta cubre los tres "
               "criterios de la evaluación: análisis de datos, automatización con IA y canales digitales.")

# ---------------------------------------------------------------- 2. Temario
items = ["Introducción", "Entorno tecnológico actual", "Necesidades tecnológicas", "Selección de tecnologías",
         "Tecnologías clave: PULSO", "Análisis de datos (2.1.1)", "Automatización con IA (2.1.2)",
         "Voz del cliente con IA", "Pruebas del modelo", "Canales digitales (2.1.3)", "Integración en la organización", "Implementación", "Gestión del cambio",
         "Impacto y mejora continua", "Conclusiones"]
col_w = ANCHO / 2
for i, it in enumerate(items):
    col, fila = divmod(i, 8)
    x, y = X0 + col * col_w, Y0 + 10 + fila * 86
    numero(temario, x, y, i + 1, size=40)
    texto(temario, x + 110, y + 8, col_w - 160, 60, it, size=32, color=GRIS)
notas(temario, "Este es el recorrido: parto por el contexto y el diagnóstico, explico qué tecnologías elegí y por "
               "qué, muestro el prototipo funcionando en sus tres módulos y cierro con la implementación, la gestión "
               "del cambio y cómo mediríamos el impacto.")

# ---------------------------------------------------------------- 3. Introducción
texto(intro, X0, Y0 + 10, 860, 60, "La organización", size=36, color=GRIS, bold=True)
texto(intro, X0, Y0 + 80, 860, 300, [
    "Olist es un marketplace de e-commerce que publica productos de miles de pymes en grandes tiendas online de "
    "Brasil. Gestiona la venta, el cobro y la logística; cada vendedor despacha su producto y el cliente evalúa la "
    "compra con una nota de 1 a 5 y un comentario.",
], size=28, color=TEXTO)
texto(intro, X0, Y0 + 400, 860, 60, "Objetivo del trabajo", size=36, color=GRIS, bold=True)
texto(intro, X0, Y0 + 470, 860, 220, [
    "Proponer y prototipar la transformación digital de Olist usando sus propios datos: decidir con información, "
    "automatizar la atención de reclamos con IA y definir los canales digitales con clientes y proveedores.",
], size=28, color=TEXTO)

stats = [("98.353", "pedidos reales analizados"), ("95.121", "clientes"),
         ("3.062", "vendedores (proveedores)"), ("39.035", "reseñas con texto para la IA")]
cx0, cw, ch, gap = 1060, 365, 290, 30
for i, (v, l) in enumerate(stats):
    c, f = i % 2, i // 2
    x, y = cx0 + c * (cw + gap), Y0 + 10 + f * (ch + gap)
    caja(intro, x, y, cw, ch, FONDO)
    texto(intro, x + 30, y + 50, cw - 60, 110, v, size=72, color=ROJO, bold=True)
    texto(intro, x + 30, y + 170, cw - 60, 80, l, size=24, color=GRIS)
texto(intro, cx0, Y0 + 2 * ch + gap + 30, 2 * cw + gap, 60,
      "Fuente: Kaggle · Brazilian E-Commerce Public Dataset by Olist (CC BY-NC-SA 4.0). Período: ene-2017 a ago-2018.",
      size=18, color=SUAVE)
notas(intro, "Olist conecta pymes con grandes vitrinas online. Elegí este caso porque tiene datos reales y "
             "públicos: pedidos, pagos, ubicación de clientes, vendedores y reseñas escritas por los clientes. Mi "
             "objetivo fue usar esos datos para tres cosas: decidir mejor, automatizar la atención y elegir canales.")

# ---------------------------------------------------------------- 4. Entorno tecnológico actual
texto(entorno, X0, Y0, 1000, 50, "Nota promedio del cliente según días de entrega", size=30, color=GRIS, bold=True)
datos = CategoryChartData()
datos.categories = ["0–7 días", "8–14", "15–21", "22–30", "+30"]
valores = (4.4, 4.3, 4.1, 3.5, 2.2)
datos.add_series("Nota promedio", valores)
gf = entorno.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Pt(X0), Pt(Y0 + 60), Pt(1000), Pt(560), datos)
gf.name = "Grafico nota por dias"
ch_ = gf.chart
ch_.has_legend = False
ch_.has_title = False
ch_.font.name = FUENTE
ch_.font.size = Pt(20)
ch_.font.color.rgb = GRIS
plot = ch_.plots[0]
plot.gap_width = 60
plot.has_data_labels = True
dl = plot.data_labels
dl.number_format = "0.0"
dl.number_format_is_linked = False
dl.position = XL_LABEL_POSITION.OUTSIDE_END
dl.font.size = Pt(24)
dl.font.bold = True
dl.font.color.rgb = TEXTO
for i, v in enumerate(valores):
    pt_ = plot.series[0].points[i]
    pt_.format.fill.solid()
    pt_.format.fill.fore_color.rgb = GRIS if v >= 4 else ROJO
    # etiqueta con coma decimal, independiente de la configuración regional
    tf_ = pt_.data_label.text_frame
    tf_.text = num_es(v)
    tf_.paragraphs[0].runs[0].font.size = Pt(24)
    tf_.paragraphs[0].runs[0].font.bold = True
    tf_.paragraphs[0].runs[0].font.color.rgb = TEXTO
    pt_.data_label.position = XL_LABEL_POSITION.OUTSIDE_END
va = ch_.value_axis
va.maximum_scale, va.minimum_scale = 5, 0
va.visible = False
va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = LINEA
va.format.line.fill.background()
va.tick_labels.font.size = Pt(18)
ca = ch_.category_axis
ca.format.line.color.rgb = LINEA
ca.tick_labels.font.size = Pt(20)
texto(entorno, X0, Y0 + 640, 1000, 60, "En rojo, los tramos bajo 4,0. Fuente: 96.478 pedidos entregados (Olist).",
      size=18, color=SUAVE)

sx = 1200
callouts = [("8,1%", "de los pedidos llega después de la fecha prometida"),
            ("4,3 → 2,6", "cae la nota del cliente cuando el pedido se atrasa"),
            ("3,0%", "de los clientes vuelve a comprar")]
for i, (v, l) in enumerate(callouts):
    y = Y0 + 10 + i * 230
    texto(entorno, sx, y, 620, 100, v, size=72, color=ROJO, bold=True)
    texto(entorno, sx, y + 105, 600, 90, l, size=24, color=GRIS)
texto(entorno, sx, Y0 + 690, 620, 60, "Hoy las reseñas se leen a mano y sin prioridad.", size=22, color=TEXTO,
      bold=True)
notas(entorno, "Este gráfico resume el problema. Cuando el pedido llega en una semana, la nota es 4,4. Pasados 30 "
               "días cae a 2,2. Un 8% de los pedidos se atrasa y con atraso la nota baja de 4,3 a 2,6. Además, solo "
               "el 3% de los clientes recompra. En el escenario actual las reseñas se revisan manualmente y no hay "
               "avisos proactivos al cliente.")

# ---------------------------------------------------------------- 5. Necesidades tecnológicas
filas = [
    ["Necesidad", "Evidencia en los datos", "Respuesta tecnológica"],
    ["Decidir con datos, no por intuición", "20 meses de ventas, 72 categorías y 27 estados sin un tablero común",
     "Dashboard analítico con hallazgos y decisiones"],
    ["Atender reclamos rápido y con prioridad", "39.035 reseñas escritas; 39% de los reclamos negativos son por entrega",
     "IA que clasifica cada reseña y asigna prioridad"],
    ["Comunicar de forma proactiva", "Con atraso la nota cae de 4,3 a 2,6; 20% paga con boleto (pago diferido)",
     "WhatsApp Business API y email automatizado"],
    ["Coordinar a los proveedores", "3.062 vendedores despachan; 21% de los reclamos negativos son de calidad",
     "Portal de vendedores e integración ERP / API"],
    ["Fidelizar a los clientes", "Solo 3,0% de los clientes compra más de una vez", "CRM con campañas post-compra"],
]
tabla(necesidades, X0, Y0 + 10, ANCHO, filas, [3, 4.4, 3.4], size=22, alto_fila=112, resaltar_col=None)
notas(necesidades, "De cada problema derivo una necesidad y una respuesta tecnológica. Lo importante es que cada "
                   "fila está respaldada por un dato real: por ejemplo, el 39% de los reclamos negativos se explica "
                   "por la entrega, y eso justifica tanto la IA como WhatsApp.")

# ---------------------------------------------------------------- 6. Selección de tecnologías
filas = [
    ["Ámbito", "Tecnología elegida", "Alternativa evaluada", "Por qué se eligió"],
    ["Análisis de datos", "Python + pandas", "Excel / Power BI", "Gratuito, reproducible y procesa 100 mil registros"],
    ["Inteligencia artificial", "scikit-learn (TF-IDF + regresión logística)", "API de IA de pago",
     "Corre en el equipo, sin costo por mensaje; 80% de precisión"],
    ["Interfaz", "App de escritorio .exe", "Aplicación web", "Funciona sin internet ni instalación"],
    ["Clientes", "WhatsApp Business API + email", "SMS / call center", "Inmediato, de bajo costo y automatizable"],
    ["Gestión de clientes", "CRM HubSpot / Zoho", "Planillas", "Importa los tickets que genera la IA"],
    ["Proveedores", "Seller Center + API ERP", "Correo manual", "Alertas automáticas por vendedor"],
]
tabla(seleccion, X0, Y0 + 10, ANCHO, filas, [2.2, 3.2, 2.4, 4.2], size=22, alto_fila=96, resaltar_col=1)
texto(seleccion, X0, Y0 + 10 + 96 * 7 + 24, ANCHO, 40,
      "Criterios: costo, facilidad de uso, integración con el resto de las plataformas y escalabilidad.",
      size=20, color=SUAVE)
notas(seleccion, "Para cada ámbito comparé alternativas con cuatro criterios: costo, facilidad, integración y "
                 "escalabilidad. Por ejemplo, para la IA preferí un modelo propio con scikit-learn en vez de una API "
                 "pagada: no cobra por mensaje, funciona sin internet y su precisión es de 80%.")

# ---------------------------------------------------------------- 7. Tecnologías clave: PULSO
texto(clave, X0, Y0, 720, 60, "PULSO · Centro de Operaciones Digitales", size=34, color=GRIS, bold=True)
texto(clave, X0, Y0 + 70, 680, 120, "Producto de escritorio (.exe) para el equipo de operaciones, funcionando sobre "
                                    "los datos reales de Olist.", size=26, color=TEXTO)
modulos = [("Inicio", "KPIs del mes, alertas y acciones rápidas", "panel diario"),
           ("Analítica", "Ventas, logística y pagos con insights", "2.1.1"),
           ("Bandeja IA", "Clasifica, explica, prioriza y responde", "2.1.2"),
           ("Voz del cliente", "Tendencia de reclamos y ranking de vendedores", "2.1.2"),
           ("Modelo IA", "Métricas, pruebas y casos generados en vivo", "2.1.2"),
           ("Canales", "Integraciones y reglas de automatización", "2.1.3")]
for i, (t, d, c) in enumerate(modulos):
    y = Y0 + 180 + i * 92
    numero(clave, X0, y, i + 1, size=40)
    texto(clave, X0 + 110, y + 2, 600, 44, [[(t, {}), (f"   {c.upper()}", {"size": 15, "color": ROJO})]],
          size=27, color=GRIS, bold=True)
    texto(clave, X0 + 110, y + 46, 600, 36, d, size=21, color=TEXTO)
_, w_, h_ = imagen(clave, "ppt/img/app_inicio.png", 830, Y0, w=990, recorte=(0, 0, 1920, 880),
                   nombre="Captura inicio")
texto(clave, 830, Y0 + h_ + 14, 990, 40, "Inicio: KPIs del último mes con tendencia, alertas generadas por los datos y "
                                         "estado de los canales.", size=18, color=SUAVE)
notas(clave, "PULSO es el prototipo: un .exe que se abre sin instalar nada. Lo diseñé como un producto real para un "
             "equipo de operaciones. Tiene cuatro módulos: Inicio, que muestra cómo va el mes y qué requiere "
             "atención; Analítica, Bandeja IA, Voz del cliente y Canales, que cubren los tres criterios de la "
             "evaluación.")

# ---------------------------------------------------------------- 8. Análisis de datos
etiqueta(s_analisis, X0, Y0 - 10, "Criterio 2.1.1 · Análisis de información con datos reales")
pic, w, h = imagen(s_analisis, "ppt/img/app_analisis.png", X0, Y0 + 40, w=1080, recorte=(270, 150, 1890, 1057),
                   nombre="Captura dashboard")
texto(s_analisis, X0, Y0 + 40 + h + 14, 1080, 40,
      "Dashboard con filtros por año, región y categoría; exporta el informe a Excel.", size=18, color=SUAVE)
hx = X0 + 1080 + 50
texto(s_analisis, hx, Y0 + 40, X1 - hx, 50, "Hallazgo → decisión", size=30, color=GRIS, bold=True)
hallazgos = [("Peak en nov-17 (Black Friday): R$ 1,01 M", "Planificar stock y campañas con 6 semanas de anticipación"),
             ("Atraso: nota 2,6 vs. 4,3 a tiempo", "Avisos proactivos por WhatsApp y medir a cada vendedor"),
             ("20% paga con boleto bancario", "Recordatorios automáticos de pago por email y WhatsApp"),
             ("Solo 3,0% de clientes recompra", "CRM y campañas post-compra")]
for i, (hh, dd) in enumerate(hallazgos):
    y = Y0 + 110 + i * 150
    numero(s_analisis, hx, y, i + 1, size=34)
    texto(s_analisis, hx + 80, y + 2, X1 - hx - 80, 70, hh, size=22, color=TEXTO, bold=True)
    texto(s_analisis, hx + 80, y + 66, X1 - hx - 80, 70, [[("→ ", {"color": ROJO, "bold": True}), (dd, {})]],
          size=21, color=GRIS)
notas(s_analisis, "Este es el módulo de análisis. Arriba están los indicadores: 13,5 millones de reales, 98 mil "
                  "pedidos, nota 4,11 y 8,1% de atrasos. Los gráficos se recalculan al filtrar. Lo importante es que "
                  "cada hallazgo termina en una decisión concreta: por ejemplo, el peak de Black Friday obliga a "
                  "planificar con seis semanas de anticipación.")

# ---------------------------------------------------------------- 9. Automatización con IA
etiqueta(s_ia, X0, Y0 - 10, "Criterio 2.1.2 · Automatización de procesos con IA")
pasos = [("Recepción", "Llega la reseña"), ("Sentimiento", "La IA clasifica"), ("Tema y área", "Motivo y responsable"),
         ("Prioridad y canal", "Plazo 2 h · 24 h · 72 h"), ("Respuesta y ticket", "Lista para el CRM")]
pw, pg = 318, 32
for i, (t, d) in enumerate(pasos):
    x = X0 + i * (pw + pg)
    c = caja(s_ia, x, Y0 + 40, pw, 130, ROJO if i == 1 else FONDO, nombre=f"Paso {i + 1}")
    col = BLANCO if i == 1 else GRIS
    texto_en(c, [[(f"{i + 1:02d}  ", {"bold": True, "size": 26, "color": col}), (t, {"bold": True, "color": col})],
                 [(d, {"size": 20, "color": BLANCO if i == 1 else TEXTO})]], size=24, align=PP_ALIGN.LEFT, margen=20)
    if i < 4:
        flecha(s_ia, x + pw + 4, Y0 + 105, x + pw + pg - 4, Y0 + 105)
pic, w, h = imagen(s_ia, "ppt/img/app_ia.png", X0, Y0 + 205, w=1180, recorte=(278, 298, 1872, 1050),
                   nombre="Captura bandeja IA")
texto(s_ia, X0, Y0 + 205 + h + 12, 1180, 40, "Bandeja procesada: prioridad, canal y ficha del ticket con la "
                                             "respuesta generada.", size=18, color=SUAVE)
mx = X0 + 1180 + 50
metricas = [("80%", "de precisión en 7.807 reseñas que el modelo no vio"),
            ("0,01 s", "para procesar 25 mensajes"),
            ("1,2 h", "ahorradas cada 25 mensajes (supuesto: 3 min por mensaje manual)")]
for i, (v, l) in enumerate(metricas):
    y = Y0 + 210 + i * 170
    texto(s_ia, mx, y, X1 - mx, 80, v, size=60, color=ROJO, bold=True)
    texto(s_ia, mx, y + 80, X1 - mx, 80, l, size=20, color=GRIS)
notas(s_ia, "Este es el proceso que automaticé: la gestión de reseñas y reclamos. El modelo se entrenó con 31 mil "
            "reseñas reales y acierta el 80% en reseñas que nunca vio. Además detecta el tema, como 'no recibido' o "
            "'producto defectuoso', y con reglas de negocio asigna prioridad, área, canal y plazo. Finalmente "
            "redacta la respuesta y exporta los tickets a Excel para cargarlos en el CRM. En la demo puedo escribir "
            "un mensaje y ver cómo lo clasifica.")

# ---------------------------------------------------------------- 9b. Voz del cliente
etiqueta(s_voz, X0, Y0 - 10, "Criterio 2.1.2 · El mismo modelo, cuatro usos más")
_, w_, h_ = imagen(s_voz, "ppt/img/app_voz.png", X0, Y0 + 40, w=1080, recorte=(262, 130, 1886, 1050),
                   nombre="Captura voz del cliente")
texto(s_voz, X0, Y0 + 40 + h_ + 12, 1080, 40, "Módulo Voz del cliente: 38.801 reseñas clasificadas por la IA.",
      size=18, color=SUAVE)
vx = X0 + 1080 + 50
usos = [("Explica cada decisión", "Muestra las palabras que pesaron: «quebrado» → negativo."),
        ("Responde en portugués", "Genera la respuesta que recibe el cliente en Brasil."),
        ("Detecta motivos en alza", "«Producto defectuoso» pasó de 4% a 6% de los reclamos."),
        ("Rankea a los vendedores", "11 vendedores en riesgo: más del doble de reseñas negativas que el promedio.")]
for i, (t, d) in enumerate(usos):
    y = Y0 + 50 + i * 168
    numero(s_voz, vx, y, i + 1, size=34)
    texto(s_voz, vx + 80, y + 2, X1 - vx - 80, 44, t, size=24, color=GRIS, bold=True)
    texto(s_voz, vx + 80, y + 48, X1 - vx - 80, 110, d, size=21, color=TEXTO)
notas(s_voz, "Con el mismo entrenamiento sumé cuatro funciones. Primero, la IA explica cada decisión mostrando las "
             "palabras que más pesaron, así se entiende por qué clasificó un mensaje como negativo. Segundo, redacta "
             "la respuesta en portugués. Tercero, al aplicarla a las casi 39 mil reseñas, detecta qué motivo de "
             "reclamo está creciendo. Y cuarto, arma un ranking de vendedores: 11 tienen más del doble de reseñas "
             "negativas que el promedio y pasan a la regla del Seller Center.")

# ---------------------------------------------------------------- 9c. Validación del modelo
# Las cifras salen de ejecutar las pruebas reales (mismo código que la app y probar_modelo.py)
import random  # noqa: E402

import app as pulso  # noqa: E402
from casos_prueba import SUITE, generar  # noqa: E402

dm = pulso.Datos()
suite = pulso.evaluar_casos(dm, [{"id": i, "tipo": t, "mensaje": m, "sentimiento": s, "tema": tm}
                                 for i, t, m, s, tm in SUITE])
rng = random.Random(7)
gen = pulso.evaluar_casos(dm, [generar(rng=rng) for _ in range(300)])
est, lim = suite[suite.tipo == "Estándar"], suite[suite.tipo == "Límite"]

etiqueta(s_valid, X0, Y0 - 10, "Criterio 2.1.2 · Cómo sabemos que la IA funciona")
texto(s_valid, X0, Y0 + 40, 820, 44, f"Matriz de confusión · {dm.n_test:,} reseñas que el modelo nunca vio".replace(
    ",", "."), size=26, color=GRIS, bold=True)
m = dm.matriz
filas_pct = m / m.sum(axis=1, keepdims=True)
gt = s_valid.shapes.add_table(4, 4, Pt(X0), Pt(Y0 + 100), Pt(820), Pt(400))
tb = gt.table
tb._tbl.tblPr.set("bandRow", "0")
tb._tbl.tblPr.set("firstRow", "0")
for j, w in enumerate([250, 190, 190, 190]):
    tb.columns[j].width = Pt(w)
cab = ["Nota real ↓ · IA →"] + dm.etiquetas
for i in range(4):
    tb.rows[i].height = Pt(100)
    for j in range(4):
        cel = tb.cell(i, j)
        cel.vertical_anchor = MSO_ANCHOR.MIDDLE
        cel.fill.solid()
        p = cel.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if j else PP_ALIGN.LEFT
        if i == 0 or j == 0:
            cel.fill.fore_color.rgb = BLANCO
            txt, col, b, sz = (cab[j] if i == 0 else dm.etiquetas[i - 1]), GRIS, True, 20 if (i or j) else 16
        else:
            v = filas_pct[i - 1, j - 1]
            acierto = i == j
            cel.fill.fore_color.rgb = (RGBColor(0x58, 0x58, 0x5A) if acierto else
                                       (RGBColor(0xF6, 0xD5, 0xD3) if v >= 0.2 else FONDO))
            txt = f"{m[i - 1, j - 1]:,}".replace(",", ".") + f"\n{v:.0%}"
            col, b, sz = (BLANCO if acierto else TEXTO), acierto, 22
        r = p.add_run()
        r.text = txt
        r.font.name, r.font.size, r.font.bold = FUENTE, Pt(sz), b
        r.font.color.rgb = col
texto(s_valid, X0, Y0 + 520, 820, 80, "Diagonal gris: aciertos. En rojo, las confusiones de 20% o más: los neutros "
                                     "se confunden con negativos y positivos.", size=19, color=SUAVE)

vx2 = X0 + 820 + 70
bloques = [(f"{dm.precision:.0%}", "de exactitud en reseñas reales no vistas"),
           (f"{suite.ok.sum()}/{len(suite)}", f"casos de la suite superados (estándar {est.ok.sum()}/{len(est)} · "
                                              f"límite {lim.ok.sum()}/{len(lim)})"),
           (f"{gen.ok.mean():.0%}", f"de {len(gen)} casos generados al azar, clasificados correctamente")]
for i, (v, l) in enumerate(bloques):
    y = Y0 + 40 + i * 170
    texto(s_valid, vx2, y, X1 - vx2, 90, v, size=64, color=ROJO, bold=True)
    texto(s_valid, vx2, y + 88, X1 - vx2, 70, l, size=21, color=GRIS)
texto(s_valid, vx2, Y0 + 560, X1 - vx2, 40, "Limitación detectada", size=24, color=GRIS, bold=True)
texto(s_valid, vx2, Y0 + 604, X1 - vx2, 110,
      f"Neutro tiene solo {dm.reporte['Neutro']['precision']:.0%} de precisión y el sarcasmo engaña al modelo: "
      "«Parabéns pela demora» sale positivo. Mejora: reentrenar con reseñas corregidas.", size=20, color=TEXTO)
notas(s_valid, "¿Cómo sé que la IA funciona? La probé de tres maneras. Primero, con casi 8 mil reseñas reales que "
               "el modelo nunca vio: acierta el 80%. La matriz muestra que es muy buena con positivos y negativos, "
               "pero débil con los neutros. Segundo, con una suite de casos escritos a mano, incluidos casos difíciles "
               "como el sarcasmo, y no todos pasan, lo que es esperable. Tercero, con un generador que crea mensajes "
               "nuevos en vivo; en la demo puedo generar uno y ver si acierta. Las fallas definen la mejora: "
               "reentrenar con las reseñas que corrijan los agentes.")

# ---------------------------------------------------------------- 10. Canales digitales
etiqueta(s_canales, X0, Y0 - 10, "Criterio 2.1.3 · Plataformas de comunicación con clientes y proveedores")
filas = [
    ["Canal / plataforma", "Público", "Uso en el proceso", "Fundamento en los datos", "Prioridad"],
    ["WhatsApp Business API", "Clientes", "Avisos de despacho y atención de reclamos de prioridad alta",
     "39% de los reclamos negativos son por entrega", "Alta"],
    ["Email transaccional", "Clientes", "Confirmaciones, recordatorio de boleto, encuestas", "20% paga con boleto",
     "Alta"],
    ["CRM (HubSpot / Zoho)", "Clientes", "Registro de tickets de la IA y fidelización", "Solo 3,0% recompra", "Alta"],
    ["Portal de vendedores", "Proveedores", "Alertas por atrasos y reclamos de calidad",
     "3.062 vendedores; 21% reclamos de calidad", "Alta"],
    ["Integración ERP / API", "Proveedores", "Sincronizar stock, precios y estado del pedido",
     "~4.900 pedidos al mes", "Media"],
    ["Redes sociales", "Clientes", "Campañas por fecha peak y reseñas positivas", "Peak en nov-17", "Media"],
    ["Teams / Slack", "Equipo interno", "Alertas de tickets críticos a cada área", "8,1% de pedidos atrasados",
     "Media"],
]
tabla(s_canales, X0, Y0 + 40, ANCHO, filas, [2.6, 1.6, 4.2, 3.6, 1.2], size=20, alto_fila=84, resaltar_col=None)
notas(s_canales, "Propongo siete plataformas, separadas por público: clientes, proveedores y equipo interno. Cada "
                 "una se justifica con un dato. WhatsApp tiene prioridad alta porque la entrega explica el 39% de "
                 "los reclamos; el email, porque uno de cada cinco pedidos se paga con boleto y hay que recordar el "
                 "pago; y el portal de vendedores, porque son 3 mil proveedores a coordinar.")

# ---------------------------------------------------------------- 11. Integración en la organización
etiqueta(s_integ, X0, Y0 - 10, "Criterio 2.1.3 · Integración con métodos y procedimientos organizacionales")
bw, bh = 330, 150
cols = [X0 + 20, X0 + 20 + 445, X0 + 20 + 890, X0 + 20 + 1335]
fila1, fila2 = Y0 + 60, Y0 + 470
estilos = {"actor": (BLANCO, GRIS, GRIS), "sistema": (GRIS, None, BLANCO), "ia": (ROJO, None, BLANCO),
           "canal": (FONDO, None, GRIS)}


def nodo(x, y, titulo, sub, estilo):
    fondo, borde, col = estilos[estilo]
    c = caja(s_integ, x, y, bw, bh, fondo, borde, MSO_SHAPE.ROUNDED_RECTANGLE, nombre=titulo)
    texto_en(c, [[(titulo, {"bold": True, "size": 26, "color": col})], [(sub, {"size": 19, "color": col})]])
    return c


nodo(cols[0], fila1, "Cliente", "compra en la web", "actor")
nodo(cols[1], fila1, "ERP + API", "pedido al vendedor", "sistema")
nodo(cols[2], fila1, "WhatsApp · Email", "avisos de despacho", "canal")
nodo(cols[3], fila1, "Cliente", "deja su reseña", "actor")
nodo(cols[3], fila2, "IA de PULSO", "sentimiento + tema", "ia")
nodo(cols[2], fila2, "CRM", "ticket con prioridad", "sistema")
nodo(cols[1], fila2, "WhatsApp · Email", "alta 2 h · media 24 h", "canal")
nodo(cols[0], fila2, "Seller Center · Teams", "alertas a vendedor y áreas", "sistema")
for a, b in ((0, 1), (1, 2), (2, 3)):
    flecha(s_integ, cols[a] + bw + 8, fila1 + bh / 2, cols[b] - 8, fila1 + bh / 2)
for a, b in ((3, 2), (2, 1), (1, 0)):
    flecha(s_integ, cols[a] - 8, fila2 + bh / 2, cols[b] + bw + 8, fila2 + bh / 2)
flecha(s_integ, cols[3] + bw / 2, fila1 + bh + 8, cols[3] + bw / 2, fila2 - 8)
flecha(s_integ, cols[0] + bw / 2, fila2 - 8, cols[0] + bw / 2, fila1 + bh + 8)
texto(s_integ, cols[0] + bw / 2 + 16, fila1 + bh + 80, 300, 80, "el dashboard mide y ajusta el proceso",
      size=19, color=SUAVE)
leyenda = [("Actor", BLANCO, GRIS), ("Sistema", GRIS, None), ("Canal", FONDO, None), ("IA", ROJO, None)]
for i, (t, f, b) in enumerate(leyenda):
    x = X0 + 20 + i * 200
    caja(s_integ, x, Y0 + 690, 30, 30, f, b)
    texto(s_integ, x + 44, Y0 + 692, 140, 30, t, size=20, color=GRIS)
notas(s_integ, "Así se integran las plataformas en el procedimiento de la empresa. El pedido entra al ERP, el "
               "vendedor despacha y el cliente recibe avisos por WhatsApp o email. Cuando deja su reseña, la IA la "
               "clasifica y crea el ticket en el CRM. Los casos urgentes se responden por WhatsApp en dos horas y "
               "las alertas llegan al vendedor por el Seller Center y a las áreas por Teams. El dashboard mide todo "
               "y cierra el ciclo de mejora.")

# ---------------------------------------------------------------- 11b. Canales en PULSO
etiqueta(s_canales_app, X0, Y0 - 10, "Criterio 2.1.3 · Las plataformas operando dentro del producto")
_, w_, h_ = imagen(s_canales_app, "ppt/img/app_canales.png", X0, Y0 + 40, w=1080, recorte=(240, 52, 1920, 1057),
                   nombre="Captura canales")
texto(s_canales_app, X0, Y0 + 40 + h_ + 12, 1080, 40, "Módulo Canales: integraciones conectables y reglas de "
                                                      "automatización.", size=18, color=SUAVE)
px = X0 + 1080 + 50
puntos = [("Cada canal se conecta o desconecta", "WhatsApp, email, CRM, Seller Center, ERP, redes y Teams, cada "
                                                 "uno con el dato que lo justifica."),
          ("8 reglas «cuando… entonces…»", "Por ejemplo: reseña negativa crítica → responder por WhatsApp en 2 horas."),
          ("Todo queda conectado", "Si se desactiva WhatsApp, la Bandeja IA deriva los casos urgentes al email y la "
                                   "regla queda en pausa.")]
for i, (t, d) in enumerate(puntos):
    y = Y0 + 50 + i * 215
    numero(s_canales_app, px, y, i + 1, size=34)
    texto(s_canales_app, px + 80, y + 2, X1 - px - 80, 80, t, size=24, color=GRIS, bold=True)
    texto(s_canales_app, px + 80, y + 76, X1 - px - 80, 120, d, size=21, color=TEXTO)
notas(s_canales_app, "Los canales no se quedan en una tabla: están implementados en el producto. Cada integración "
                     "se activa o desactiva y las reglas de automatización definen qué pasa en cada caso. En la demo "
                     "puedo desconectar WhatsApp y mostrar cómo la bandeja deriva al email los reclamos urgentes.")

# ---------------------------------------------------------------- 12. Implementación
fases = [("Fase 1", "Mes 1", "Datos", "Integrar ventas, logística y reseñas; lanzar el dashboard",
          "Gerencia comercial"),
         ("Fase 2", "Mes 2", "IA piloto", "Clasificación automática con revisión humana en Atención al Cliente",
          "Atención al cliente"),
         ("Fase 3", "Mes 3", "Canales", "WhatsApp Business API, email automatizado y CRM con los tickets",
          "Marketing y TI"),
         ("Fase 4", "Meses 4–6", "Proveedores", "Seller Center, integración ERP y escalamiento a todas las "
                                                "categorías", "Operaciones")]
fw, fgap = 405, 33
ty = Y0 + 70
conector = caja(implem, X0, ty + 26, ANCHO, 4, LINEA)
for i, (f, m, t, d, r) in enumerate(fases):
    x = X0 + i * (fw + fgap)
    caja(implem, x, ty, 56, 56, ROJO if i == 0 else GRIS, forma=MSO_SHAPE.OVAL)
    texto(implem, x + 76, ty + 6, fw - 80, 50, f"{f} · {m}", size=24, color=ROJO if i == 0 else GRIS, bold=True)
    c = caja(implem, x, ty + 100, fw, 470, FONDO)
    texto(implem, x + 30, ty + 130, fw - 60, 60, t, size=34, color=GRIS, bold=True)
    texto(implem, x + 30, ty + 200, fw - 60, 220, d, size=23, color=TEXTO)
    texto(implem, x + 30, ty + 460, fw - 60, 30, "RESPONSABLE", size=16, color=SUAVE, bold=True)
    texto(implem, x + 30, ty + 492, fw - 60, 50, r, size=22, color=GRIS, bold=True)
texto(implem, X0, ty + 600, ANCHO, 40, "Cada fase entrega valor por sí sola y se evalúa antes de pasar a la "
                                       "siguiente.", size=20, color=SUAVE)
notas(implem, "La implementación va en cuatro fases. Primero los datos, porque sin información confiable no hay "
              "IA. Luego un piloto de IA con revisión humana. Después se conectan los canales y finalmente se suma a "
              "los proveedores. Cada fase tiene un responsable y entrega valor por sí sola.")

# ---------------------------------------------------------------- 13. Gestión del cambio
pilares = [("Personas", ["Capacitar a los agentes en el uso de la bandeja de IA",
                         "Guía rápida y webinar para los vendedores",
                         "Líderes de cambio en cada área"]),
           ("Procesos", ["Nuevo protocolo de reclamos con plazos de 2 h, 24 h y 72 h",
                         "Revisión humana de las respuestas de la IA durante el piloto",
                         "Indicadores semanales por vendedor"]),
           ("Comunicación", ["Explicar el porqué con los datos del diagnóstico",
                             "Mostrar resultados tempranos del piloto",
                             "Canal de sugerencias para el equipo"])]
pw2, pg2 = 545, 42
for i, (t, lst) in enumerate(pilares):
    x = X0 + i * (pw2 + pg2)
    caja(cambio, x, Y0 + 10, pw2, 390, FONDO)
    numero(cambio, x + 30, Y0 + 36, i + 1, size=44)
    texto(cambio, x + 140, Y0 + 46, pw2 - 170, 50, t, size=32, color=GRIS, bold=True)
    texto(cambio, x + 30, Y0 + 130, pw2 - 60, 340, [[("—  ", {"color": ROJO, "bold": True}), (l, {})] for l in lst],
          size=23, color=TEXTO, espacio=18)
texto(cambio, X0, Y0 + 450, 600, 40, "Riesgos y mitigación", size=28, color=GRIS, bold=True)
riesgos = [("Resistencia al cambio", "piloto acotado y beneficios visibles"),
           ("Errores de la IA (20%)", "un agente revisa los casos de prioridad alta"),
           ("Datos personales", "cumplimiento de la LGPD (ley brasileña de datos)")]
for i, (r, m) in enumerate(riesgos):
    x = X0 + i * (pw2 + pg2)
    texto(cambio, x, Y0 + 510, pw2, 100, [[(r, {"bold": True, "color": ROJO})], [(m, {})]], size=22, color=TEXTO,
          espacio=4)
notas(cambio, "La tecnología no basta si las personas no la adoptan. Trabajo en tres frentes: personas, procesos y "
              "comunicación. El riesgo principal es que la IA se equivoca en un 20% de los casos; por eso, en el "
              "piloto un agente revisa los casos de prioridad alta antes de responder. También se cuida la ley "
              "brasileña de protección de datos, la LGPD.")

# ---------------------------------------------------------------- 14. Impacto y mejora continua
filas = [
    ["Indicador", "Línea base (datos reales)", "Meta a 6 meses", "Cómo se mide"],
    ["Pedidos atrasados", "8,1%", "menos de 5%", "Dashboard PULSO"],
    ["Nota promedio del cliente", "4,11", "4,30", "Reseñas"],
    ["Clientes que recompran", "3,0%", "5,0%", "CRM"],
    ["Primera respuesta a reclamos urgentes", "Sin plazo definido", "menos de 2 horas", "Tickets del CRM"],
    ["Reseñas revisadas a mano", "100%", "solo prioridad alta", "Bandeja de IA"],
]
tabla(impacto, X0, Y0 + 10, 1150, filas, [3.4, 2.6, 2.2, 2.2], size=22, alto_fila=100, resaltar_col=2)
cx = X0 + 1150 + 60
texto(impacto, cx, Y0 + 10, X1 - cx, 50, "Ciclo de mejora continua", size=28, color=GRIS, bold=True)
ciclo = ["Medir en el dashboard", "Analizar desvíos", "Ajustar reglas y canales", "Reentrenar la IA con nuevas reseñas"]
for i, c in enumerate(ciclo):
    y = Y0 + 80 + i * 130
    b = caja(impacto, cx, y, X1 - cx, 100, ROJO if i == 3 else FONDO)
    texto_en(b, [[(f"{i + 1:02d}  ", {"bold": True, "color": BLANCO if i == 3 else ROJO}),
                  (c, {"color": BLANCO if i == 3 else GRIS})]], size=23, align=PP_ALIGN.LEFT, margen=24)
    if i < 3:
        flecha(impacto, cx + 60, y + 104, cx + 60, y + 126)
notas(impacto, "Para saber si funciona fijé metas medibles sobre la línea base real. Por ejemplo, bajar los "
               "atrasos de 8,1% a menos de 5% y subir la recompra de 3% a 5%. Todo se mide con la misma app y el "
               "CRM. El ciclo de mejora termina reentrenando la IA con las reseñas nuevas, así el modelo mejora con "
               "el uso.")

# ---------------------------------------------------------------- 15. Conclusiones
conclusiones = [
    ("Los datos señalan dónde actuar", "La logística es el principal motor de insatisfacción: con atraso, la nota "
                                       "cae de 4,3 a 2,6."),
    ("La IA automatiza un proceso real", "Clasifica y prioriza reseñas con 80% de precisión y responde en "
                                         "segundos, sin costo por mensaje."),
    ("Los canales se eligen con evidencia", "WhatsApp, email, CRM y el portal de vendedores responden a datos "
                                            "concretos del negocio."),
    ("La transformación es gradual", "Cuatro fases, gestión del cambio y metas medibles para mejorar de forma "
                                     "continua."),
]
for i, (t, d) in enumerate(conclusiones):
    c, f = i % 2, i // 2
    x, y = X0 + c * (ANCHO / 2 + 20), Y0 + 20 + f * 340
    w_ = ANCHO / 2 - 20
    caja(concl, x, y, w_, 300, FONDO)
    numero(concl, x + 36, y + 36, i + 1, size=56)
    texto(concl, x + 36, y + 130, w_ - 72, 50, t, size=30, color=GRIS, bold=True)
    texto(concl, x + 36, y + 186, w_ - 72, 100, d, size=23, color=TEXTO)
notas(concl, "Cierro con cuatro ideas. Los datos muestran que la logística es el problema central. La IA "
             "automatiza un proceso concreto y medible. Los canales se eligieron con evidencia, no por moda. Y la "
             "transformación se implementa por fases, con metas claras.")

# ---------------------------------------------------------------- 16. Bibliografía
refs = [
    "Olist & Sionek, A. (2018). Brazilian E-Commerce Public Dataset by Olist [Conjunto de datos]. Kaggle. "
    "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, "
    "12, 2825–2830.",
    "McKinney, W. (2010). Data structures for statistical computing in Python. Proceedings of the 9th Python in "
    "Science Conference, 56–61.",
    "Meta. (s. f.). WhatsApp Business Platform: documentación para desarrolladores. "
    "https://developers.facebook.com/docs/whatsapp",
    "Brasil. (2018). Lei n.º 13.709, Lei Geral de Proteção de Dados Pessoais (LGPD).",
    "INACAP. (2024). Electivo Transformación Digital, Unidad 2: Herramientas digitales, canales digitales, "
    "plataformas digitales para comunicación y automatización de procesos con IA [Material de clase].",
]
texto(biblio, X0, Y0 + 10, ANCHO, 700, [[(r, {})] for r in refs], size=24, color=TEXTO, espacio=26)
notas(biblio, "Las fuentes: el dataset de Olist en Kaggle, las librerías utilizadas, la documentación de WhatsApp "
              "Business, la ley de datos de Brasil y el material de la Unidad 2.")

notas(cierre, "Gracias. Si hay tiempo, muestro la app en vivo: filtrar el dashboard, procesar la bandeja de IA y "
              "probar un mensaje propio.")

prs.save("ppt/Evaluacion2_PULSO_Olist.pptx")
print("ok", len(prs.slides), "diapositivas")
