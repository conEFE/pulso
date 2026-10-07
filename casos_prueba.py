"""
Casos de prueba del modelo de PULSO y generador de casos nuevos.

Cada caso trae su resultado ESPERADO (sentimiento y tema) escrito a mano; la prueba compara ese esperado
con lo que entrega el sistema. Los casos "Límite" son difíciles a propósito (sarcasmo, mensajes muy cortos,
mayúsculas, faltas de ortografía, negaciones) y no se espera que todos pasen.
"""
import random

ELOGIO = "Elogio / comentario positivo"

# (id, tipo, mensaje, sentimiento esperado, tema esperado)
SUITE = [
    ("C01", "Estándar", "Não recebi meu pedido e já passou o prazo de entrega", "Negativo", "No recibido"),
    ("C02", "Estándar", "Comprei há um mês e o produto ainda não chegou", "Negativo", "No recibido"),
    ("C03", "Estándar", "O produto chegou quebrado, quero trocar urgente", "Negativo", "Producto defectuoso"),
    ("C04", "Estándar", "A tela veio danificada e o aparelho não funciona", "Negativo", "Producto defectuoso"),
    ("C05", "Estándar", "Quero cancelar a compra e receber meu dinheiro de volta", "Negativo",
     "Reembolso / cancelación"),
    ("C06", "Estándar", "Solicitei a devolução há duas semanas e o estorno não foi feito", "Negativo",
     "Reembolso / cancelación"),
    ("C07", "Estándar", "Veio a cor errada e faltou uma peça do kit", "Negativo", "Producto incorrecto o incompleto"),
    ("C08", "Estándar", "Pedi dois itens e veio apenas um", "Negativo", "Producto incorrecto o incompleto"),
    ("C09", "Estándar", "A entrega demorou muito mais do que o prometido", "Negativo", "Retraso en la entrega"),
    ("C10", "Estándar", "O vendedor não responde minhas mensagens, péssimo atendimento", "Negativo",
     "Atención del vendedor"),
    ("C11", "Estándar", "Material de péssima qualidade, rasgou no primeiro uso", "Negativo", "Calidad del producto"),
    ("C12", "Estándar", "Produto bom, mas a entrega atrasou alguns dias", "Neutro", "Retraso en la entrega"),
    ("C13", "Estándar", "O produto é ok, nada demais", "Neutro", "General"),
    ("C14", "Estándar", "Chegou certinho, mas a embalagem poderia ser melhor", "Neutro", "General"),
    ("C15", "Estándar", "Adorei! Chegou antes do prazo e muito bem embalado", "Positivo", ELOGIO),
    ("C16", "Estándar", "Excelente produto, recomendo a loja", "Positivo", ELOGIO),
    ("C17", "Estándar", "Tudo perfeito, entrega rápida e produto de ótima qualidade", "Positivo", ELOGIO),
    ("C18", "Estándar", "Muito satisfeita com a compra, voltarei a comprar", "Positivo", ELOGIO),
    ("L01", "Límite", "Ótimo, mais uma vez atrasou. Parabéns pela demora", "Negativo", "Retraso en la entrega"),
    ("L02", "Límite", "ok", "Neutro", "General"),
    ("L03", "Límite", "NAO GOSTEI", "Negativo", "General"),
    ("L04", "Límite", "Produto lindo, porém veio com defeito no zíper", "Negativo", "Producto defectuoso"),
    ("L05", "Límite", "produto chego rapido gostei mto", "Positivo", ELOGIO),
    ("L06", "Límite", "Não tenho do que reclamar", "Positivo", ELOGIO),
]

# ---------------------------------------------------------------- generador de casos nuevos
PRODUCTOS = ["o fone de ouvido", "a panela", "o relógio", "a cadeira", "o jogo de toalhas", "a luminária",
             "o tênis", "a mochila", "o liquidificador", "o perfume", "a capa de celular", "o tapete"]
TIEMPOS = ["duas semanas", "dez dias", "um mês", "quinze dias", "vinte dias"]
CIERRE_NEG = ["", " Que decepção.", " Quero uma solução.", " Estou muito chateado.", " Não recomendo."]
CIERRE_POS = ["", " Recomendo!", " Voltarei a comprar.", " Muito obrigado!"]

# escenario: (sentimiento esperado, [(plantilla, tema esperado)], cierres)
ESCENARIOS = {
    "No recibido": ("Negativo", [
        ("Comprei {prod} há {tiempo} e ainda não chegou.", "No recibido"),
        ("Não recebi {prod} e o prazo já venceu.", "No recibido"),
        ("Até hoje não recebi {prod}.", "No recibido"),
        ("O rastreio diz entregue, mas não recebi {prod}.", "No recibido"),
    ], CIERRE_NEG),
    "Producto defectuoso": ("Negativo", [
        ("{Prod} chegou quebrado.", "Producto defectuoso"),
        ("{Prod} veio com defeito e não funciona.", "Producto defectuoso"),
        ("Recebi {prod} todo amassado.", "Producto defectuoso"),
        ("{Prod} parou de funcionar no segundo dia, veio com defeito.", "Producto defectuoso"),
    ], CIERRE_NEG),
    "Reembolso / cancelación": ("Negativo", [
        ("Quero cancelar a compra de {prod} e receber meu dinheiro de volta.", "Reembolso / cancelación"),
        ("Pedi a devolução de {prod} há {tiempo} e o estorno não caiu.", "Reembolso / cancelación"),
        ("Solicito o reembolso de {prod} imediatamente.", "Reembolso / cancelación"),
    ], CIERRE_NEG),
    "Producto incorrecto": ("Negativo", [
        ("Pedi {prod} e veio outro produto.", "Producto incorrecto o incompleto"),
        ("{Prod} veio na cor errada.", "Producto incorrecto o incompleto"),
        ("Comprei dois itens e veio apenas {prod}.", "Producto incorrecto o incompleto"),
        ("O pedido veio incompleto, faltou {prod}.", "Producto incorrecto o incompleto"),
    ], CIERRE_NEG),
    "Retraso": ("Negativo", [
        ("{Prod} demorou {tiempo} para chegar.", "Retraso en la entrega"),
        ("A entrega de {prod} atrasou muito.", "Retraso en la entrega"),
        ("O prazo não foi cumprido, {prod} chegou com {tiempo} de atraso.", "Retraso en la entrega"),
    ], CIERRE_NEG),
    "Neutro": ("Neutro", [
        ("{Prod} é bom, mas a entrega atrasou um pouco.", "Retraso en la entrega"),
        ("{Prod} é ok, nada de especial.", "General"),
        ("Chegou {prod}, mas esperava um pouco mais pelo preço.", "General"),
    ], [""]),
    "Positivo": ("Positivo", [
        ("Adorei {prod}, chegou antes do prazo!", ELOGIO),
        ("{Prod} é excelente, recomendo.", ELOGIO),
        ("Muito satisfeito com {prod}, ótima qualidade.", ELOGIO),
        ("Entrega rápida e {prod} perfeito.", ELOGIO),
    ], CIERRE_POS),
}


def generar(escenario=None, rng=random):
    """Arma un mensaje nuevo para el escenario (o uno al azar) con su resultado esperado."""
    escenario = escenario if escenario in ESCENARIOS else rng.choice(list(ESCENARIOS))
    sent, plantillas, cierres = ESCENARIOS[escenario]
    plantilla, tema = rng.choice(plantillas)
    prod = rng.choice(PRODUCTOS)
    texto = plantilla.format(prod=prod, Prod=prod[0].upper() + prod[1:], tiempo=rng.choice(TIEMPOS))
    return {"escenario": escenario, "mensaje": texto + rng.choice(cierres), "sentimiento": sent, "tema": tema}
