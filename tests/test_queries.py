import sqlite3

import pandas as pd
import pytest

from src.build_db import ROOT, build
from src.run_queries import query_files, run

SQL = ROOT / "sql"


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    c = build(tmp_path_factory.mktemp("db") / "test.db")
    c.executescript((SQL / "views.sql").read_text(encoding="utf-8"))
    return c


def test_reconciliation_finds_exactly_the_planted_breaks(con):
    found = pd.read_sql_query(
        "SELECT payment_id, exception_type AS break_type FROM v_recon_exceptions", con)
    planted = pd.read_sql_query("SELECT payment_id, break_type FROM breaks", con)
    key = ["payment_id", "break_type"]
    assert found.sort_values(key).reset_index(drop=True).equals(
        planted.sort_values(key).reset_index(drop=True))


def test_recon_summary_counts_match_answer_key(con):
    summary = run(con, SQL / "01_recon_summary.sql").set_index("exception_type")["exceptions"]
    planted = pd.read_sql_query(
        "SELECT break_type, COUNT(*) n FROM breaks GROUP BY break_type", con
    ).set_index("break_type")["n"]
    assert summary.sort_index().to_dict() == planted.sort_index().to_dict()


def test_every_query_runs(con):
    for path in query_files():
        assert len(run(con, path)) > 0, path.name


def test_daily_kpis_add_up(con):
    k = run(con, SQL / "11_daily_kpis.sql")
    total = con.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    assert k["attempts"].sum() == total
    assert k["success_rate_pct"].between(0, 100).all()


def test_chargeback_rate_on_a_small_example():
    c = sqlite3.connect(":memory:")
    c.executescript((SQL / "00_schema.sql").read_text(encoding="utf-8"))
    c.execute("INSERT INTO merchants VALUES ('M1','Shop','grocery','Gauteng',2.0,'2025-01-01')")
    for i in range(200):
        c.execute("INSERT INTO payments VALUES (?, 'M1', '2026-07-01 10:00:00', 100, 'ZAR', "
                  "'card', 'Bank A', 'succeeded', NULL, 0)", (f"P{i}",))
    for i in range(3):
        c.execute("INSERT INTO chargebacks VALUES (?, ?, 'M1', '2026-07-10 10:00:00', 100, "
                  "'fraud_card_not_present', 'cardholder_won')", (f"CB{i}", f"P{i}"))
    r = run(c, SQL / "08_chargeback_rate_by_merchant.sql").iloc[0]
    assert r["chargeback_rate_pct"] == pytest.approx(1.5)
    assert r["flag"] == "review"
