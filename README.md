# Payments SQL Analytics

SQL analysis of a quarter of payments for a South African payment service provider: reconciliation against the bank's settlement file, failed payments, retry recovery, chargebacks and settlement, with a Power BI dashboard design. The SQL runs on SQLite, so it needs nothing beyond Python to run.

## Findings

| Area | Finding |
| --- | --- |
| Reconciliation | 170 exceptions worth about R319 000, including 30 duplicate settlements and 27 unsettled payments older than 30 days |
| Failed payments | Bank F fails 13.9% of card payments against about 8% elsewhere, and 45% of its failures are timeouts: a technical fault, not declines |
| Retries | 54% of timeouts succeed on a retry within 15 minutes, against 3.5% of insufficient funds failures |
| Chargebacks | 5 merchants are above the 1% monitoring level, driven by card not present fraud |

Full write up: [reports/findings.md](reports/findings.md)

![Dashboard preview](reports/figures/dashboard_preview.png)

## SQL

| File | What it does | Techniques |
| --- | --- | --- |
| `views.sql` | Reconciliation exceptions between ledger and bank file | CTEs, `UNION ALL`, anti joins, `ROW_NUMBER` and `COUNT` window functions |
| `01_recon_summary.sql` | Exceptions and value at stake by type | `CASE` aggregation |
| `02_recon_exceptions.sql` | Exception list with next action for operations | Joins, `COALESCE` |
| `03_unsettled_ageing.sql` | Ageing of payments missing from the bank file | Date arithmetic, bucketing |
| `04_failure_rates.sql` | Failure rate and timeout share by channel and bank | Conditional aggregation, `NULLIF` |
| `05_failure_reasons.sql` | Failure reasons ranked within channel | `RANK`, windowed `SUM` |
| `06_failure_by_hour.sql` | Failure rate by hour | `strftime` |
| `07_retry_recovery.sql` | Failed payments recovered by a retry within 15 minutes | Self join on a time window |
| `08_chargeback_rate_by_merchant.sql` | Merchants above the 1% chargeback level | Multiple CTEs, `RANK` |
| `09_chargeback_reasons.sql` | Win rate and value lost by reason | Conditional aggregation |
| `10_merchant_settlement.sql` | Monthly gross, fees and net per merchant | Running total with `SUM OVER` |
| `11_daily_kpis.sql` | Daily volume, success rate, ticket size | 7 day moving average with `ROWS BETWEEN` |
| `12_merchant_growth.sql` | Month on month growth by category | `LAG` |

## How The Data Works

The data is synthetic (`src/generate_data.py`): 60 merchants, about 50 000 payment attempts over July to September 2026, the bank's settlement file and chargebacks. The settlement file is broken on purpose in the five ways real files go wrong, and every planted break is stored in a `breaks` table. The tests check that the reconciliation SQL finds exactly those breaks, no more and no fewer.

## Power BI

The dashboard design, data model, and DAX measures are in [powerbi/](powerbi/README.md). Load the CSVs from `outputs/` into Power BI Desktop and follow the steps there.

## Setup (Windows)

```
git clone https://github.com/LusandaNongogo/payments-sql-analytics.git
cd payments-sql-analytics
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py -m src.run_queries
py -m src.charts
py -m pytest
```

`run_queries` builds `payments.db` and writes every query result to `outputs/`. To explore the database directly, open `payments.db` in [DB Browser for SQLite](https://sqlitebrowser.org/).
