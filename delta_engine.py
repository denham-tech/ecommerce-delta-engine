"""
E-Commerce Delta Engine
Computes granular diffs between catalog snapshots:
- Price changes
- Stockouts
- Added products
- Removed products
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DeltaEngine")


class DeltaEngine:
    """Calculates deltas across consecutive catalog runs."""

    def __init__(self):
        pass

    def compute_deltas(self, baseline: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
        """Compares baseline and current DataFrames to isolate state changes."""
        deltas = []

        b_df = baseline.copy()
        c_df = current.copy()

        # Identify match key: prefer 'sku', fallback to 'product_id' or 'id'
        key = "sku" if "sku" in b_df.columns and "sku" in c_df.columns else "id"

        b_df[key] = b_df[key].astype(str)
        c_df[key] = c_df[key].astype(str)

        b_keys = set(b_df[key].dropna())
        c_keys = set(c_df[key].dropna())

        # 1. PRODUCT_ADDED
        added_keys = c_keys - b_keys
        for ak in added_keys:
            row = c_df[c_df[key] == ak].iloc[0]
            deltas.append({
                "event_type": "PRODUCT_ADDED",
                "key": ak,
                "title": row.get("title", ""),
                "price": row.get("price", 0.0),
                "detail": f"Product added: {row.get('title', ak)}"
            })

        # 2. PRODUCT_REMOVED
        removed_keys = b_keys - c_keys
        for rk in removed_keys:
            row = b_df[b_df[key] == rk].iloc[0]
            deltas.append({
                "event_type": "PRODUCT_REMOVED",
                "key": rk,
                "title": row.get("title", ""),
                "price": row.get("price", 0.0),
                "detail": f"Product removed: {row.get('title', rk)}"
            })

        # 3. Intersecting products: evaluate PRICE_CHANGE and STOCKOUT
        common_keys = b_keys.intersection(c_keys)
        for ck in common_keys:
            b_row = b_df[b_df[key] == ck].iloc[0]
            c_row = c_df[c_df[key] == ck].iloc[0]

            # Price Change
            try:
                b_price = float(b_row.get("price", 0.0))
                c_price = float(c_row.get("price", 0.0))
                if b_price != c_price:
                    deltas.append({
                        "event_type": "PRICE_CHANGE",
                        "key": ck,
                        "title": c_row.get("title", ""),
                        "price": c_price,
                        "old_price": b_price,
                        "detail": f"Price adjusted from {b_price} to {c_price}"
                    })
            except (ValueError, TypeError):
                pass

            # Stockout (available was True, now False)
            b_avail = str(b_row.get("available", "")).strip().lower() in ("true", "1")
            c_avail = str(c_row.get("available", "")).strip().lower() in ("true", "1")

            if b_avail and not c_avail:
                deltas.append({
                    "event_type": "STOCKOUT",
                    "key": ck,
                    "title": c_row.get("title", ""),
                    "price": c_row.get("price", 0.0),
                    "detail": f"Stockout detected for {c_row.get('title', ck)}"
                })

        return pd.DataFrame(deltas)

    def persist_deltas(
        self,
        delta_df: pd.DataFrame,
        output_csv: str = "delta_results.csv",
        db_path: Optional[str] = None
    ) -> None:
        """Saves detected deltas to disk."""
        delta_df.to_csv(output_csv, index=False)
        logger.info("Persisted %d deltas to %s", len(delta_df), output_csv)


# Module-level alias for unit test compatibility
CatalogDeltaEngine = DeltaEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E-Commerce Catalog Delta Processor")
    parser.add_argument("--baseline", required=True, help="Baseline snapshot CSV")
    parser.add_argument("--current", required=True, help="Current snapshot CSV")
    parser.add_argument("--output", default="delta_results.csv", help="Output path for deltas")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = DeltaEngine()

    b_df = pd.read_csv(args.baseline)
    c_df = pd.read_csv(args.current)

    deltas = engine.compute_deltas(b_df, c_df)
    engine.persist_deltas(deltas, output_csv=args.output)
    logger.info("Delta pipeline complete: %d changes recorded.", len(deltas))


if __name__ == "__main__":
    main()