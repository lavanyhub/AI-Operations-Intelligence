import json
import os
import uuid

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from scripts.profit_bridge import bridge_from_sales

router = APIRouter()
UPLOAD_DIR = "data/uploads"
REQUIRED = ["date", "product", "units", "price", "unit_cost"]


@router.post("/datasets")
async def upload_dataset(file: UploadFile = File(...), mapping: str = Form(...)):
    """
    mapping is JSON saying which of the company's columns means what, e.g.
    {"date": "Order Date", "product": "Item", "units": "Qty",
     "price": "Selling Price", "unit_cost": "Cost Price"}
    """
    try:
        mapping = json.loads(mapping)
    except json.JSONDecodeError:
        raise HTTPException(400, "mapping must be valid JSON")

    missing = [k for k in REQUIRED if k not in mapping]
    if missing:
        raise HTTPException(400, f"mapping is missing: {missing}")

    try:
        df = pd.read_csv(file.file)
    except Exception:
        raise HTTPException(400, "Could not read the file as CSV")

    not_found = [v for v in mapping.values() if v not in df.columns]
    if not_found:
        raise HTTPException(400, f"These columns are not in your file: {not_found}. "
                                 f"Your file has: {list(df.columns)}")

    # Rename the company's columns to our standard names
    df = df.rename(columns={mapping[k]: k for k in REQUIRED})[REQUIRED]
    total_rows = len(df)

    # Clean: convert types, drop rows that cannot be used
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["units", "price", "unit_cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    df = df[(df["units"] > 0) & (df["price"] >= 0) & (df["unit_cost"] >= 0)]

    if len(df) == 0:
        raise HTTPException(400, "No usable rows after cleaning. Check your column mapping.")

    dataset_id = uuid.uuid4().hex[:8]
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    df.to_csv(f"{UPLOAD_DIR}/{dataset_id}.csv", index=False)

    return {
        "dataset_id": dataset_id,
        "rows_used": len(df),
        "rows_dropped": total_rows - len(df),
        "date_from": str(df["date"].min().date()),
        "date_to": str(df["date"].max().date()),
        "products": int(df["product"].nunique()),
    }


@router.get("/datasets/{dataset_id}/profit-bridge")
def dataset_profit_bridge(dataset_id: str, before_start: str, before_end: str,
                          after_start: str, after_end: str):
    path = f"{UPLOAD_DIR}/{dataset_id}.csv"
    if not os.path.exists(path):
        raise HTTPException(404, "Dataset not found")

    sales = pd.read_csv(path)
    result = bridge_from_sales(sales, before_start, before_end, after_start, after_end)
    return {
        "total_change": float(result["total_change"].sum()),
        "volume_effect": float(result["volume_effect"].sum()),
        "price_effect": float(result["price_effect"].sum()),
        "cost_effect": float(result["cost_effect"].sum()),
        "top_losers": result.sort_values("total_change").head(5).reset_index().to_dict(orient="records"),
        "top_gainers": result.sort_values("total_change", ascending=False).head(5).reset_index().to_dict(orient="records"),
    }