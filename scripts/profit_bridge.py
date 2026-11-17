import pandas as pd


def profit_bridge(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """
    Each input has columns: product, units, price, unit_cost
    (one row per product for that period).
    Returns one row per product with volume, price, cost effects
    and the total change in profit.
    """
    a = before.set_index("product")
    b = after.set_index("product")
    products = a.index.union(b.index)
    a = a.reindex(products)
    b = b.reindex(products)

    # Product missing in one period: zero units, and reuse the other
    # period's price/cost so only the volume effect shows up.
    a["units"] = a["units"].fillna(0)
    b["units"] = b["units"].fillna(0)
    for col in ["price", "unit_cost"]:
        a[col] = a[col].fillna(b[col])
        b[col] = b[col].fillna(a[col])

    out = pd.DataFrame(index=products)
    out["volume_effect"] = (b["units"] - a["units"]) * (a["price"] - a["unit_cost"])
    out["price_effect"] = (b["price"] - a["price"]) * b["units"]
    out["cost_effect"] = -(b["unit_cost"] - a["unit_cost"]) * b["units"]
    out["total_change"] = (
        b["units"] * (b["price"] - b["unit_cost"])
        - a["units"] * (a["price"] - a["unit_cost"])
    )
    return out.round(2)


def bridge_from_sales(sales: pd.DataFrame, before_start, before_end, after_start, after_end) -> pd.DataFrame:
    """
    sales columns: date, product, units, price, unit_cost (one row per sale).
    Periods are inclusive date ranges, e.g. "2026-01-01", "2026-03-31".
    """
    sales = sales.copy()
    sales["date"] = pd.to_datetime(sales["date"])
    sales["revenue"] = sales["units"] * sales["price"]
    sales["cost"] = sales["units"] * sales["unit_cost"]

    def summarize(start, end):
        part = sales[(sales["date"] >= pd.to_datetime(start)) & (sales["date"] <= pd.to_datetime(end))]
        g = part.groupby("product").agg(units=("units", "sum"), revenue=("revenue", "sum"), cost=("cost", "sum"))
        g = g[g["units"] > 0]
        g["price"] = g["revenue"] / g["units"]
        g["unit_cost"] = g["cost"] / g["units"]
        return g.reset_index()[["product", "units", "price", "unit_cost"]]

    return profit_bridge(summarize(before_start, before_end), summarize(after_start, after_end))