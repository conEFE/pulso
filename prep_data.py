"""
Prepara los datos reales de Olist (Kaggle: Brazilian E-Commerce Public Dataset)
y entrena el modelo de IA que usa la app.

Entrada:  raw/*.csv  (descargados de github.com/olist/work-at-olist-data)
Salida:   data/ventas.csv.gz    -> un registro por pedido (para el dashboard)
          data/resenas.csv.gz   -> reseñas con texto (para la bandeja de la IA)
          data/modelo_ia.joblib -> clasificador de sentimiento + métricas
"""
import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

RAW = "raw"
OUT = "data"
os.makedirs(OUT, exist_ok=True)

CATEGORIAS_ES = {
    "health_beauty": "Salud y belleza", "computers_accessories": "Computación y accesorios",
    "auto": "Automotriz", "bed_bath_table": "Cama, baño y mesa", "furniture_decor": "Muebles y decoración",
    "sports_leisure": "Deportes y ocio", "perfumery": "Perfumería", "housewares": "Artículos del hogar",
    "telephony": "Telefonía", "watches_gifts": "Relojes y regalos", "food_drink": "Alimentos y bebidas",
    "baby": "Bebés", "stationery": "Papelería", "toys": "Juguetes", "garden_tools": "Jardinería",
    "fashion_bags_accessories": "Bolsos y accesorios", "small_appliances": "Pequeños electrodomésticos",
    "consoles_games": "Consolas y videojuegos", "audio": "Audio", "fashion_shoes": "Calzado",
    "cool_stuff": "Artículos novedosos", "luggage_accessories": "Maletas y accesorios",
    "pet_shop": "Mascotas", "office_furniture": "Muebles de oficina", "electronics": "Electrónica",
    "home_appliances": "Electrodomésticos", "musical_instruments": "Instrumentos musicales",
    "books_general_interest": "Libros", "computers": "Computadores", "drinks": "Bebidas", "food": "Alimentos",
    "construction_tools_construction": "Herramientas de construcción", "home_construction": "Construcción hogar",
    "kitchen_dining_laundry_garden_furniture": "Cocina y lavandería", "fashion_male_clothing": "Ropa hombre",
    "fashio_female_clothing": "Ropa mujer", "industry_commerce_and_business": "Industria y comercio",
    "agro_industry_and_commerce": "Agroindustria", "party_supplies": "Artículos de fiesta",
    "christmas_supplies": "Navidad", "flowers": "Flores", "art": "Arte",
}

ESTADO_REGION = {
    **dict.fromkeys(["SP", "RJ", "MG", "ES"], "Sudeste"),
    **dict.fromkeys(["PR", "SC", "RS"], "Sur"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA"], "Nordeste"),
    **dict.fromkeys(["AM", "PA", "AC", "RO", "RR", "AP", "TO"], "Norte"),
}

PAGO_ES = {"credit_card": "Tarjeta de crédito", "boleto": "Boleto bancario",
           "voucher": "Voucher", "debit_card": "Tarjeta de débito"}


def construir_ventas():
    fechas = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(f"{RAW}/olist_orders_dataset.csv", parse_dates=fechas)
    items = pd.read_csv(f"{RAW}/olist_order_items_dataset.csv")
    pays = pd.read_csv(f"{RAW}/olist_order_payments_dataset.csv")
    revs = pd.read_csv(f"{RAW}/olist_order_reviews_dataset.csv")
    custs = pd.read_csv(f"{RAW}/olist_customers_dataset.csv")
    prods = pd.read_csv(f"{RAW}/olist_products_dataset.csv")
    trad = pd.read_csv(f"{RAW}/product_category_name_translation.csv")

    # Periodo con datos completos
    orders = orders[(orders.order_purchase_timestamp >= "2017-01-01") &
                    (orders.order_purchase_timestamp < "2018-09-01")]

    prods = prods.merge(trad, on="product_category_name", how="left")
    prods["categoria"] = prods.product_category_name_english.map(
        lambda c: CATEGORIAS_ES.get(c, str(c).replace("_", " ").capitalize() if pd.notna(c) else "Sin categoría"))
    items = items.merge(prods[["product_id", "categoria"]], on="product_id", how="left")

    # Agregado por pedido: valor, flete, nº ítems, vendedor y categoría principal
    it = items.groupby("order_id").agg(
        valor=("price", "sum"), flete=("freight_value", "sum"), items=("order_item_id", "count"),
        vendedor=("seller_id", "first"), categoria=("categoria", "first")).reset_index()

    pg = (pays.sort_values("payment_value", ascending=False)
          .groupby("order_id").agg(pago=("payment_type", "first"), cuotas=("payment_installments", "max"))
          .reset_index())
    pg["pago"] = pg.pago.map(PAGO_ES).fillna("Otro")

    rv = revs.groupby("order_id").agg(nota=("review_score", "mean")).reset_index()

    df = (orders.merge(custs[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id")
          .merge(it, on="order_id").merge(pg, on="order_id", how="left").merge(rv, on="order_id", how="left"))

    df["fecha"] = df.order_purchase_timestamp.dt.date
    df["estado"] = df.customer_state
    df["region"] = df.estado.map(ESTADO_REGION)
    df["dias_entrega"] = (df.order_delivered_customer_date - df.order_purchase_timestamp).dt.days
    df["atrasado"] = (df.order_delivered_customer_date > df.order_estimated_delivery_date).astype("Int8")
    df.loc[df.order_delivered_customer_date.isna(), "atrasado"] = pd.NA
    df["estado_pedido"] = df.order_status

    # IDs anónimos de 32 caracteres -> códigos enteros (el archivo pesa mucho menos)
    df["customer_unique_id"] = pd.factorize(df.customer_unique_id)[0]
    df["vendedor"] = pd.factorize(df.vendedor)[0]
    mapa = df[["order_id", "vendedor", "categoria"]]

    cols = ["customer_unique_id", "fecha", "estado", "region", "categoria", "vendedor",
            "valor", "flete", "items", "pago", "cuotas", "nota", "dias_entrega", "atrasado", "estado_pedido"]
    df = df[cols].rename(columns={"customer_unique_id": "cliente"})
    df["valor"] = df.valor.round(2)
    df["flete"] = df.flete.round(2)
    df.to_csv(f"{OUT}/ventas.csv.gz", index=False, compression="gzip")
    print(f"ventas: {len(df):,} pedidos")
    return mapa


def sentimiento(nota):
    return "Negativo" if nota <= 2 else ("Neutro" if nota == 3 else "Positivo")


def entrenar_ia(mapa):
    revs = pd.read_csv(f"{RAW}/olist_order_reviews_dataset.csv")
    revs = revs[revs.review_comment_message.notna()].copy()
    revs["texto"] = revs.review_comment_message.str.replace(r"\s+", " ", regex=True).str.strip()
    revs = revs[revs.texto.str.len() >= 8]
    revs["sentimiento"] = revs.review_score.map(sentimiento)

    train, test = train_test_split(revs, test_size=0.2, random_state=42, stratify=revs.sentimiento)

    modelo = Pipeline([
        ("tfidf", TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2),
                                  min_df=3, max_features=30000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, C=4, class_weight="balanced")),
    ])
    modelo.fit(train.texto, train.sentimiento)
    pred = modelo.predict(test.texto)
    acc = accuracy_score(test.sentimiento, pred)
    print(classification_report(test.sentimiento, pred))

    etiquetas = ["Negativo", "Neutro", "Positivo"]
    joblib.dump({"modelo": modelo, "accuracy": acc, "n_train": len(train), "n_test": len(test),
                 "etiquetas": etiquetas,
                 "matriz": confusion_matrix(test.sentimiento, pred, labels=etiquetas),
                 "reporte": classification_report(test.sentimiento, pred, labels=etiquetas, output_dict=True)},
                f"{OUT}/modelo_ia.joblib", compress=3)

    # Solo reseñas que el modelo NO vio: simulan los mensajes nuevos que llegan
    test = test.rename(columns={"review_creation_date": "fecha", "review_score": "nota"})
    test[["review_id", "order_id", "fecha", "nota", "sentimiento", "texto"]].to_csv(
        f"{OUT}/resenas.csv.gz", index=False, compression="gzip")
    print(f"IA: accuracy {acc:.1%} sobre {len(test):,} reseñas de prueba")

    # Voz del cliente: la IA clasifica TODAS las reseñas con texto y se cruzan con vendedor y categoría
    revs["sent_ia"] = modelo.predict(revs.texto)
    voz = revs.rename(columns={"review_creation_date": "fecha", "review_score": "nota"})
    voz = voz[["order_id", "fecha", "nota", "sentimiento", "sent_ia", "texto"]].merge(mapa, on="order_id", how="left")
    voz["vendedor"] = voz.vendedor.astype("Int64")
    voz.drop(columns="order_id").to_csv(f"{OUT}/voz_cliente.csv.gz", index=False, compression="gzip")
    print(f"voz del cliente: {len(voz):,} reseñas clasificadas")


if __name__ == "__main__":
    entrenar_ia(construir_ventas())
