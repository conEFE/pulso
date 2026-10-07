"""
Prueba el modelo de PULSO desde la terminal:
  1. métricas sobre las reseñas de prueba que el modelo nunca vio,
  2. la suite de casos escritos a mano (estándar y límite),
  3. N casos generados al azar por escenario.
Guarda el detalle en reporte_pruebas.xlsx.

Uso:  python probar_modelo.py [N_generados]
"""
import random
import sys

import pandas as pd

import app
from casos_prueba import SUITE, generar

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300

d = app.Datos()
print("=" * 70)
print(f"1. Reseñas reales no vistas: {d.n_test:,} · exactitud {d.precision:.1%}")
rep = d.reporte
print(f"   {'Clase':<10}{'Precisión':>11}{'Recall':>9}{'F1':>8}{'Soporte':>10}")
for c in d.etiquetas:
    r = rep[c]
    print(f"   {c:<10}{r['precision']:>11.1%}{r['recall']:>9.1%}{r['f1-score']:>8.2f}{int(r['support']):>10,}")

suite = app.evaluar_casos(d, [{"id": i, "tipo": t, "mensaje": m, "sentimiento": s, "tema": tm}
                              for i, t, m, s, tm in SUITE])
print("=" * 70)
print(f"2. Suite de casos: {suite.ok.sum()}/{len(suite)} superados")
for tipo, g in suite.groupby("tipo"):
    print(f"   {tipo:<9} {g.ok.sum()}/{len(g)}  (sentimiento {g.ok_sent.mean():.0%} · tema {g.ok_tema.mean():.0%})")
for _, r in suite[~suite.ok].iterrows():
    print(f"   ✗ {r['id']} «{r.mensaje}» esperado {r.sentimiento}/{r.tema} → IA {r.sent_ia}/{r.tema_ia}")

rng = random.Random(7)
gen = app.evaluar_casos(d, [generar(rng=rng) for _ in range(N)])
print("=" * 70)
print(f"3. Casos generados: {gen.ok.sum()}/{len(gen)} superados ({gen.ok.mean():.0%})")
for esc, g in gen.groupby("escenario"):
    print(f"   {esc:<24} {g.ok.mean():>5.0%}  (n={len(g)})")
print("=" * 70)

with pd.ExcelWriter("reporte_pruebas.xlsx") as xw:
    pd.DataFrame({"clase": d.etiquetas,
                  "precision": [rep[c]["precision"] for c in d.etiquetas],
                  "recall": [rep[c]["recall"] for c in d.etiquetas],
                  "f1": [rep[c]["f1-score"] for c in d.etiquetas],
                  "soporte": [rep[c]["support"] for c in d.etiquetas]}).to_excel(xw, sheet_name="Métricas", index=False)
    suite.to_excel(xw, sheet_name="Suite", index=False)
    gen.to_excel(xw, sheet_name="Generados", index=False)
print("Detalle guardado en reporte_pruebas.xlsx")
