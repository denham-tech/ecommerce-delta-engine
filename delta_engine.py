"""
Relational Catalog Delta Engine
Compares current e-commerce catalog snapshots against baseline data
to identify new variants, stockouts, and price shifts.
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Tuple
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DeltaEngine")


class CatalogDeltaEngine:
    def __init__(self, db_path: str = "warehouse.db"):
        self.db_path = db_path

    def load_snapshot(self, file_path: str) -> pd.DataFrame:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {file_path}")
        df = pd.read_csv(path)
        required = {"variant_id", "title", "sku", "price", "available"}
        if not required.issubset(df.columns):
            raise ValueError(f"File missing required columns: {required - set(df.columns)}")
        return df

    def compute_deltas(self, baseline_df: pd.DataFrame, current_df: pd.DataFrame) -> pd.DataFrame:
        """
        Performs an outer relational merge on variant_id to calculate state transitions.
        """
        merged = pd.merge(
            baseline_df,
            current_df,
            on="variant_id",
            how="outer",
            suffixes=("_prev", "_curr")
        )

        deltas = []
        for _, row in merged.iterrows():
            variant_id = row["variant_id"]

            # Scenario 1: New SKU Added
            if pd.isna(row["price_prev"]):
                deltas.append({
                    "variant_id": variant_id,
                    "event_type": "PRODUCT_ADDED",
                    "title": row["title_curr"],
                    "sku": row["sku_curr"],
                    "price_delta": 0.0,
                    "detail": f"New item introduced at ${row['price_curr']:.2f}"
                })
                continue

            # Scenario 2: SKU Removed / Delisted
            if pd.isna(row["price_curr"]):
                deltas.append({
                    "variant_id": variant_id,
                    "event_type": "PRODUCT_REMOVED",
                    "title": row["title_prev"],
                    "sku": row["sku_prev"],
                    "price_delta": 0.0,
                    "detail": "Variant removed from active storefront catalog"
                })
                continue

            # Scenario 3: Price Change
            price_prev = float(row["price_prev"])
            price_curr = float(row["price_curr"])
            if price_curr != price_prev:
                pct_change = round(((price_curr - price_prev) / price_prev) * 100, 2)
                deltas.append({
                    "variant_id": variant_id,
                    "event_type": "PRICE_CHANGE",
                    "title": row["title_curr"],
                    "sku": row["sku_curr"],
                    "price_delta": round(price_curr - price_prev, 2),
                    "detail": f"Price adjusted {pct_change}% (${price_prev:.2f} -> ${price_curr:.2f})"
                })

            # Scenario 4: Inventory State Shift (Stockout / Restock)
            avail_prev = bool(row["available_prev"])
            avail_curr = bool(row["available_curr"])
            if avail_prev != avail_curr:
                event = "RESTOCK" if avail_curr else "STOCKOUT"
                deltas.append({
                    "variant_id": variant_id,
                    "event_type": event,
                    "title": row["title_curr"],
                    "sku": row["sku_curr"],
                    "price_delta": 0.0,
                    "detail": f"Availability transitioned from {avail_prev} to {avail_curr}"
                })

        delta_df = pd.DataFrame(deltas)
        return delta_df

    def persist_deltas(self, delta_df: pd.DataFrame, output_csv: str) -> None:
        if delta_df.empty:
            logger.info("No delta events detected between catalog snapshots.")
            return

        delta_df.to_csv(output_csv, index=False)
        logger.info(f"Successfully recorded {len(delta_df)} deltas to {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="Compute change deltas between two catalog snapshots.")
    parser.add_argument("--baseline", "-b", required=True, help="Path to previous catalog snapshot CSV")
    parser.add_argument("--current", "-c", required=True, help="Path to latest catalog snapshot CSV")
    parser.add_argument("--output", "-o", default="delta_results.csv", help="Path to export delta CSV")

    args = parser.parse_args()

    engine = CatalogDeltaEngine()
    try:
        baseline_df = engine.load_snapshot(args.baseline)
        current_df = engine.load_snapshot(args.current)
    except Exception as e:
        logger.critical(f"Data loading failed: {e}")
        sys.exit(1)

    delta_df = engine.compute_deltas(baseline_df, current_df)
    engine.persist_deltas(delta_df, args.output)


if __name__ == "__main__":
    main()