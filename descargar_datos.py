"""
Descarga los CSV originales del Brazilian E-Commerce Public Dataset by Olist (los mismos de Kaggle)
desde el repositorio público de Olist en GitHub, a la carpeta raw/. Después: python prep_data.py
"""
import os
import urllib.request

BASE = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets"
ARCHIVOS = ["olist_orders_dataset.csv", "olist_order_items_dataset.csv", "olist_order_payments_dataset.csv",
            "olist_order_reviews_dataset.csv", "olist_customers_dataset.csv", "olist_products_dataset.csv",
            "product_category_name_translation.csv"]

os.makedirs("raw", exist_ok=True)
for nombre in ARCHIVOS:
    destino = os.path.join("raw", nombre)
    if os.path.exists(destino):
        print(f"ya existe  {nombre}")
        continue
    print(f"bajando    {nombre} …")
    urllib.request.urlretrieve(f"{BASE}/{nombre}", destino)
print("Listo. Ahora: python prep_data.py")
