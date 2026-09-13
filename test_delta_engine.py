import pandas as pd
from delta_engine import CatalogDeltaEngine


def test_compute_deltas_handles_add_remove_price_and_stockout():
    engine = CatalogDeltaEngine()

    baseline = pd.DataFrame({
        "variant_id": [101, 102, 103],
        "title": ["Item A", "Item B", "Item C"],
        "sku": ["SKU-A", "SKU-B", "SKU-C"],
        "price": [50.0, 30.0, 100.0],
        "available": [True, True, True]
    })

    current = pd.DataFrame({
        "variant_id": [101, 102, 104],
        "title": ["Item A", "Item B", "Item D"],
        "sku": ["SKU-A", "SKU-B", "SKU-D"],
        "price": [40.0, 30.0, 120.0],
        "available": [True, False, True]
    })

    deltas = engine.compute_deltas(baseline, current)
    events = set(deltas["event_type"].tolist())

    assert "PRICE_CHANGE" in events
    assert "STOCKOUT" in events
    assert "PRODUCT_REMOVED" in events
    assert "PRODUCT_ADDED" in events
    assert len(deltas) == 4