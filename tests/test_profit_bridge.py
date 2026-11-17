import pandas as pd
from scripts.profit_bridge import profit_bridge


def test_single_product_matches_hand_calculation():
    before = pd.DataFrame([{"product": "A", "units": 100, "price": 500, "unit_cost": 300}])
    after = pd.DataFrame([{"product": "A", "units": 90, "price": 480, "unit_cost": 330}])
    r = profit_bridge(before, after).loc["A"]
    assert r["volume_effect"] == -2000
    assert r["price_effect"] == -1800
    assert r["cost_effect"] == -2700
    assert r["total_change"] == -6500


def test_effects_always_add_up_to_total():
    before = pd.DataFrame([
        {"product": "A", "units": 100, "price": 500, "unit_cost": 300},
        {"product": "B", "units": 50, "price": 200, "unit_cost": 120},
    ])
    after = pd.DataFrame([
        {"product": "A", "units": 90, "price": 480, "unit_cost": 330},
        {"product": "C", "units": 40, "price": 300, "unit_cost": 150},  # new product, B discontinued
    ])
    r = profit_bridge(before, after)
    parts = r["volume_effect"] + r["price_effect"] + r["cost_effect"]
    assert (parts - r["total_change"]).abs().max() < 0.01