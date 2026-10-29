"""Build the SQLite database from the generated data."""

import sqlite3
from pathlib import Path

import pandas as pd

from src.generate_data import generate

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "payments.db"


def build(path=DB_PATH, seed=None):
    data = generate() if seed is None else generate(seed)
    path = Path(path)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript((ROOT / "sql" / "00_schema.sql").read_text(encoding="utf-8"))
    for name, df in data.items():
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            elif df[col].dtype == object and len(df) and hasattr(df[col].iloc[0], "isoformat"):
                df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
            elif df[col].dtype == bool:
                df[col] = df[col].astype(int)
        df.to_sql(name, con, if_exists="append", index=False)
    con.commit()
    return con


if __name__ == "__main__":
    build()
    print(f"built {DB_PATH}")
