# E-Commerce Catalog Delta Engine

Relational delta processing engine designed to isolate state changes between e-commerce catalog snapshots. Computes SKU-level additions, removals, stockout transitions, and price fluctuations across batch crawl intervals.

## Core Capabilities
- **Relational Snapshot Diffing:** Outer merge comparison on variant primary keys (`variant_id`).
- **State Transition Classification:** Identifies `PRODUCT_ADDED`, `PRODUCT_REMOVED`, `PRICE_CHANGE`, `STOCKOUT`, and `RESTOCK`.
- **CLI & Automated Reporting:** Accepts external baseline and current snapshot CSVs, writing deterministic delta reports.

## Usage

```bash
# Compare consecutive catalog crawl snapshots
python delta_engine.py --baseline data/snapshot_day1.csv --current data/snapshot_day2.csv --output delta_results.csv