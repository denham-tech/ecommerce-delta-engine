# E-Commerce Inventory & Price Delta Engine

Autonomous telemetry and change-detection engine built with **Python**, **Pandas**, and **SQLite**. Computes daily storefront snapshot deltas to detect competitor pricing shifts, variant stockouts, and catalog anomalies across multi-SKU retail environments.

## Core Capabilities
- **Relational Snapshot Analysis:** Inner-merges sequential crawl states on normalized variant IDs to isolate pricing and stock deviations.
- **Automated Anomaly Detection:** Filters non-zero delta variance and availability status shifts.
- **Relational Sink & Audit Delivery:** Generates clean executive CSV anomaly reports and logs historical deltas to an audit SQLite database.

## Architecture
- `delta_engine.py` - Ingestion, relational diffing, and persistence pipeline.
- `catalog_delta_report.csv` - Operational client-facing delta deliverable (untracked).
- `delta_warehouse.db` - Persistent relational store for historical trend analysis (untracked).