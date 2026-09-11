import sqlite3
import pandas as pd
from datetime import datetime

class InventoryDeltaEngine:
    def __init__(self, db_path: str = "delta_warehouse.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)

    def load_snapshots(self, previous_csv: str, current_csv: str):
        """
        Loads baseline and current crawl snapshots into normalized DataFrames.
        """
        df_prev = pd.read_csv(previous_csv)
        df_curr = pd.read_csv(current_csv)

        # Force required schemas
        df_prev["price"] = pd.to_numeric(df_prev["price"], errors="coerce")
        df_curr["price"] = pd.to_numeric(df_curr["price"], errors="coerce")

        return df_prev, df_curr

    def compute_deltas(self, df_prev: pd.DataFrame, df_curr: pd.DataFrame) -> pd.DataFrame:
        """
        Performs an outer relational merge on variant_id to isolate price shifts and stock status.
        """
        merged = pd.merge(
            df_prev,
            df_curr,
            on="variant_id",
            suffixes=("_prev", "_curr"),
            how="inner"
        )

        # Calculate absolute and percentage price shift
        merged["price_delta"] = merged["price_curr"] - merged["price_prev"]
        merged["price_change_pct"] = ((merged["price_delta"] / merged["price_prev"]) * 100).round(2)

        # Flag inventory changes (available -> out of stock or vice-versa)
        merged["stock_status_changed"] = merged["available_prev"] != merged["available_curr"]

        # Filter for significant business events
        anomalies = merged[
            (merged["price_delta"] != 0) | (merged["stock_status_changed"] == True)
        ].copy()

        # Build clean audit presentation
        deliverable = pd.DataFrame({
            "variant_id": anomalies["variant_id"],
            "title": anomalies["title_curr"],
            "sku": anomalies["sku_curr"],
            "old_price": anomalies["price_prev"],
            "new_price": anomalies["price_curr"],
            "price_delta": anomalies["price_delta"],
            "change_pct": anomalies["price_change_pct"],
            "was_in_stock": anomalies["available_prev"],
            "is_in_stock": anomalies["available_curr"],
            "audit_timestamp": datetime.utcnow().isoformat()
        })

        return deliverable

    def persist_deltas(self, delta_df: pd.DataFrame):
        """
        Exports audit report to CSV and logs anomalies into SQLite table.
        """
        if delta_df.empty:
            print("[*] Scan complete: Zero price or stock deltas detected.")
            return

        csv_out = "catalog_delta_report.csv"
        delta_df.to_csv(csv_out, index=False)
        print(f"[✓] Exported {len(delta_df)} anomaly alerts to {csv_out}")

        delta_df.to_sql("inventory_deltas", self.conn, if_exists="append", index=False)
        print(f"[✓] Appended delta log into {self.db_path} (Table: 'inventory_deltas')")

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    # Operational demonstration using mock delta snapshots
    import numpy as np

    # Generate synthetic previous baseline
    baseline_data = {
        "variant_id": [101, 102, 103, 104, 105],
        "title": ["Core Crewneck - Black", "Denim Trouser - Raw", "Leather Utility Belt", "Boxy Tee - White", "Heavy Hoodie - Olive"],
        "sku": ["CRW-BLK-M", "DNM-RAW-32", "BLT-LTH-OS", "TEE-WHT-L", "HD-OLV-XL"],
        "price": [95.0, 160.0, 75.0, 45.0, 130.0],
        "available": [True, True, True, True, False]
    }
    pd.DataFrame(baseline_data).to_csv("snapshot_t0.csv", index=False)

    # Generate synthetic current snapshot with competitor shifts
    current_data = {
        "variant_id": [101, 102, 103, 104, 105],
        "title": ["Core Crewneck - Black", "Denim Trouser - Raw", "Leather Utility Belt", "Boxy Tee - White", "Heavy Hoodie - Olive"],
        "sku": ["CRW-BLK-M", "DNM-RAW-32", "BLT-LTH-OS", "TEE-WHT-L", "HD-OLV-XL"],
        "price": [85.0, 160.0, 75.0, 50.0, 130.0],  # 101 discounted, 104 increased
        "available": [True, False, True, True, True]     # 102 stocked out, 105 restocked
    }
    pd.DataFrame(current_data).to_csv("snapshot_t1.csv", index=False)

    engine = InventoryDeltaEngine()
    t0, t1 = engine.load_snapshots("snapshot_t0.csv", "snapshot_t1.csv")
    deltas = engine.compute_deltas(t0, t1)
    engine.persist_deltas(deltas)
    engine.close()