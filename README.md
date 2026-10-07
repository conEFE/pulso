# PULSO · Centro de Operaciones Digitales

App de escritorio para Windows que aplica transformación digital a un e-commerce con datos reales: analítica
comercial, una bandeja de reclamos atendida por IA, la voz del cliente y las integraciones con los canales digitales.

El espacio de trabajo de ejemplo es **Olist Store**, un marketplace brasileño, con el
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(Kaggle, licencia CC BY-NC-SA 4.0): ~98 mil pedidos y ~39 mil reseñas escritas, de 2017 y 2018.

## Instalar

Descarga desde **Releases** una de estas dos opciones (Windows de 64 bits; no necesita Python):

| Archivo | Uso |
|---|---|
| `PULSO_Setup_1.3.0.exe` | Instalador con asistente: acceso en el menú Inicio, ícono opcional en el escritorio y desinstalador. No pide permisos de administrador. Abre en ~3 s. |
| `PulsoDigital.exe` | Portable: un solo archivo, sin instalar. Tarda ~15 s en abrir porque se descomprime cada vez. |

Como el ejecutable no está firmado, Windows puede mostrar "Windows protegió su PC". Elige *Más información →
Ejecutar de todas formas*.

## Módulos

| Módulo | Qué hace |
|---|---|
| Inicio | KPIs del último mes con tendencia, alertas generadas por los datos, acciones rápidas y estado de los canales |
| Analítica | Ventas, logística y pagos con filtros por año, región y categoría; insights con acción recomendada; exportación a Excel |
| Bandeja IA | Clasifica cada reseña (sentimiento y tema), explica qué palabras pesaron, asigna prioridad, área y canal, redacta la respuesta en español y portugués y exporta los tickets para un CRM |
| Voz del cliente | La IA aplicada a todas las reseñas: tendencia de reclamos, motivo en alza y ranking de vendedores en riesgo |
| Modelo IA | Matriz de confusión y métricas por clase, suite de casos de prueba y generador de casos nuevos en vivo |
| Canales | 7 integraciones conectables y 8 reglas de automatización; al desactivar un canal, la bandeja se ajusta sola |

Las integraciones son simuladas: la app no envía mensajes reales por WhatsApp ni por correo.

## El modelo de IA

TF-IDF (palabras y pares de palabras) + regresión logística, entrenado con 31.228 reseñas reales en portugués.

| | Precisión | Recall |
|---|---|---|
| Positivo | 94% | 86% |
| Negativo | 77% | 81% |
| Neutro | 21% | 31% |

Exactitud global: **80%** sobre 7.807 reseñas que el modelo no vio. Limitaciones conocidas: los mensajes neutros y
el sarcasmo. `python probar_modelo.py` ejecuta todas las pruebas y guarda `reporte_pruebas.xlsx`.

## Ejecutar desde el código

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Los datos procesados y el modelo ya vienen en `data/`. Para regenerarlos desde cero:

```
python descargar_datos.py
python prep_data.py
```

## Compilar

`build.bat` crea el entorno, compila el portable y la versión en carpeta con PyInstaller y, si
[Inno Setup 6](https://jrsoftware.org/isinfo.php) está instalado, genera el instalador. Todo queda en `dist\`.

Si `prep_data.py` se corre con otra versión de scikit-learn, hay que recompilar con esa misma versión, porque el
modelo guardado depende de ella.

## Archivos

| Archivo | Contenido |
|---|---|
| `app.py` | La aplicación |
| `casos_prueba.py` | Suite de casos de prueba y generador de casos |
| `prep_data.py` | Une los CSV de Olist y entrena el modelo |
| `descargar_datos.py` | Baja los CSV originales a `raw/` |
| `probar_modelo.py` | Pruebas del modelo por terminal |
| `build.bat`, `installer/pulso.iss` | Compilación del .exe y del instalador |
| `build_deck.py`, `make_icon.py` | Presentación de la evaluación (necesita la plantilla, que no está en el repositorio) e ícono |
