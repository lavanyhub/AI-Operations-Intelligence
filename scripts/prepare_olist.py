import pandas as pd
o=pd.read_csv("data/raw/olist_orders_dataset.csv",parse_dates=["order_purchase_timestamp"])
i=pd.read_csv("data/raw/olist_order_items_dataset.csv")
p=pd.read_csv("data/raw/olist_products_dataset.csv")
t=pd.read_csv("data/raw/product_category_name_translation.csv")
o=o[o.order_status=="delivered"][["order_id","order_purchase_timestamp"]]
d=i.merge(o,on="order_id").merge(p[["product_id","product_category_name"]],on="product_id",how="left").merge(t,on="product_category_name",how="left")
out=pd.DataFrame({"date":d.order_purchase_timestamp.dt.date,"product":d.product_category_name_english.fillna("unknown"),"units":1,"price":d.price,"unit_cost":d.freight_value})
out.to_csv("data/raw/olist_clean.csv",index=False)
print(len(out),out.date.min(),out.date.max())
