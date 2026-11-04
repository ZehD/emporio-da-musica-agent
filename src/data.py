"""Load and clean the store's CSVs once, at startup.

The CSVs are the system of record. Everything the agent knows about
products, stock, promotions and orders comes from here, through the tools.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Store:
    products: pd.DataFrame      # one row per product, with category name and active promo
    orders: pd.DataFrame
    order_items: pd.DataFrame
    customers: pd.DataFrame
    categories: pd.DataFrame


def _read(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / f"{name}.csv", dtype=str, keep_default_na=False)
    # Some files use Windows line endings; strip stray whitespace everywhere.
    return df.apply(lambda col: col.str.strip())


def load_store() -> Store:
    categories = _read("categories")
    categories["category_id"] = categories["category_id"].astype(int)

    products = _read("products")
    products["product_id"] = products["product_id"].astype(int)
    products["category_id"] = products["category_id"].astype(int)
    products["price_brl"] = products["price_brl"].astype(float)
    products["stock_quantity"] = products["stock_quantity"].astype(int)
    products = products.merge(
        categories[["category_id", "name"]].rename(columns={"name": "category"}),
        on="category_id",
        how="left",
    )

    # Only active promotions count for prices (spec B10, D11).
    promotions = _read("promotions")
    promotions["product_id"] = promotions["product_id"].astype(int)
    promotions["discount_percent"] = promotions["discount_percent"].astype(float)
    active = promotions[promotions["is_active"] == "1"]
    active = active.sort_values("discount_percent").drop_duplicates("product_id", keep="last")
    # Expired promotions are kept as plain text, so the agent can say a promotion
    # has ended instead of pretending it never existed (manual §7.3).
    expired = promotions[promotions["is_active"] != "1"].drop_duplicates(["product_id", "description", "discount_percent"])
    ended = expired.groupby("product_id").apply(
        lambda g: [f"{r.description} ({r.discount_percent:g}%)" for r in g.itertuples()], include_groups=False
    ).rename("ended_promos")
    products = products.merge(ended, on="product_id", how="left")
    products = products.merge(
        active[["product_id", "discount_percent", "description"]].rename(
            columns={"discount_percent": "promo_percent", "description": "promo_name"}
        ),
        on="product_id",
        how="left",
    )

    orders = _read("orders")
    orders["order_id"] = orders["order_id"].astype(int)
    orders["customer_id"] = orders["customer_id"].astype(int)
    orders["total_brl"] = orders["total_brl"].astype(float)

    order_items = _read("order_items")
    order_items["order_id"] = order_items["order_id"].astype(int)
    order_items["product_id"] = order_items["product_id"].astype(int)
    order_items["quantity"] = order_items["quantity"].astype(int)

    customers = _read("customers")
    customers["customer_id"] = customers["customer_id"].astype(int)

    return Store(products, orders, order_items, customers, categories)
