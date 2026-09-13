def persist_deltas(self, delta_df: pd.DataFrame, output_csv: str = "delta_results.csv", db_path: str = None) -> None:
        if delta_df.empty:
            logger.info("No delta events detected between catalog snapshots.")
            return

        # Export to CSV
        delta_df.to_csv(output_csv, index=False)
        logger.info(f"Successfully recorded {len(delta_df)} deltas to {output_csv}")

        # Optional SQLite persistence
        if db_path:
            with sqlite3.connect(db_path) as conn:
                delta_df.to_sql("catalog_deltas", conn, if_exists="append", index=False)
            logger.info(f"Appended deltas to SQLite table 'catalog_deltas' in {db_path}")


def main():
    parser = argparse.ArgumentParser(description="Compute change deltas between two catalog snapshots.")
    parser.add_argument("--baseline", "-b", required=True, help="Path to previous catalog snapshot CSV")
    parser.add_argument("--current", "-c", required=True, help="Path to latest catalog snapshot CSV")
    parser.add_argument("--output", "-o", default="delta_results.csv", help="Path to export delta CSV")
    parser.add_argument("--db", type=str, default=None, help="Optional SQLite database path to store delta records")

    args = parser.parse_args()

    engine = CatalogDeltaEngine()
    try:
        baseline_df = engine.load_snapshot(args.baseline)
        current_df = engine.load_snapshot(args.current)
    except Exception as e:
        logger.critical(f"Data loading failed: {e}")
        sys.exit(1)

    delta_df = engine.compute_deltas(baseline_df, current_df)
    engine.persist_deltas(delta_df, output_csv=args.output, db_path=args.db)