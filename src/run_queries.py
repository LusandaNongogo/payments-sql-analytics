"""Build the database, run every analysis query and export the results.

Each numbered file in sql/ is one query. Results go to outputs/ as CSV,
ready to load into Power BI or Excel.

    py -m src.run_queries
"""

import sqlite3
from pathlib import Path

import pandas as pd

from src.build_db import DB_PATH, ROOT, build

SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "outputs"


def connect(path=DB_PATH, rebuild=False):
    con = build(path) if rebuild or not Path(path).exists() else sqlite3.connect(path)
    con.executescript((SQL_DIR / "views.sql").read_text(encoding="utf-8"))
    return con


def query_files():
    return sorted(p for p in SQL_DIR.glob("[0-9][0-9]_*.sql") if p.name != "00_schema.sql")


def run(con, path):
    return pd.read_sql_query(Path(path).read_text(encoding="utf-8"), con)


def main():
    con = connect(rebuild=True)
    OUT_DIR.mkdir(exist_ok=True)
    for path in query_files():
        df = run(con, path)
        df.to_csv(OUT_DIR / f"{path.stem}.csv", index=False)
        print(f"{path.stem}: {len(df)} rows")
    # tables for the dashboard data model
    for table in ["merchants", "payments", "chargebacks"]:
        pd.read_sql_query(f"SELECT * FROM {table}", con).to_csv(OUT_DIR / f"table_{table}.csv", index=False)


if __name__ == "__main__":
    main()
