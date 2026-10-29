"""Synthetic payments data for a South African payment service provider.

Tables
  merchants     the businesses taking payments
  payments      our internal ledger: every payment attempt and its outcome
  settlements   the acquiring bank's daily settlement file
  chargebacks   disputes raised by cardholders

The settlement file is built from the ledger and then broken on purpose,
the same way real files go wrong: some payments are missing from the bank
file, some appear in the bank file but not in our ledger, some amounts
differ, some lines are duplicated and some settle a day late. Every
planted break is recorded in `breaks`, so the reconciliation queries can be
tested against a known answer.
"""

import numpy as np
import pandas as pd

START = pd.Timestamp("2026-07-01")
DAYS = 92
SEED = 11

FAILURE_REASONS = {
    "insufficient_funds": 0.45,
    "issuer_declined": 0.20,
    "invalid_card": 0.08,
    "3ds_failed": 0.15,
    "timeout": 0.07,
    "suspected_fraud": 0.05,
}
CHARGEBACK_REASONS = {
    "fraud_card_not_present": 0.45,
    "goods_not_received": 0.25,
    "not_as_described": 0.15,
    "duplicate_charge": 0.10,
    "cancelled_recurring": 0.05,
}
CATEGORIES = ["grocery", "fuel", "fashion", "electronics", "food_delivery",
              "airtime_data", "travel", "education"]
BANKS = ["Bank A", "Bank B", "Bank C", "Bank D", "Bank E", "Bank F"]


def _merchants(rng, n=60):
    cats = rng.choice(CATEGORIES, n)
    # a few merchants have weak fraud controls, which shows up in chargebacks
    risky = rng.random(n) < 0.08
    return pd.DataFrame({
        "merchant_id": [f"M{i:03d}" for i in range(n)],
        "merchant_name": [f"{c.replace('_', ' ').title()} Merchant {i:03d}" for i, c in enumerate(cats)],
        "category": cats,
        "province": rng.choice(["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape",
                                "Free State", "Limpopo", "Mpumalanga", "North West",
                                "Northern Cape"], n, p=[.36, .2, .17, .07, .05, .05, .04, .04, .02]),
        "mdr_pct": np.round(rng.uniform(1.2, 2.9, n), 2),  # merchant discount rate
        "onboarded": [START - pd.Timedelta(days=int(d)) for d in rng.integers(30, 900, n)],
        "high_risk": risky,
    })


def _payments(rng, merchants, n=60_000):
    m = merchants.sample(n, replace=True, weights=rng.pareto(1.2, len(merchants)) + 0.2,
                         random_state=SEED).reset_index(drop=True)
    day = rng.integers(0, DAYS, n)
    # more activity at month end (payday) and in the evening
    payday = ((START + pd.to_timedelta(day, "D")).day >= 25)
    keep = rng.random(n) < np.where(payday, 1.0, 0.75)
    hour = np.clip(rng.normal(15, 4.5, n).round(), 0, 23).astype(int)
    ts = START + pd.to_timedelta(day, "D") + pd.to_timedelta(hour, "h") \
        + pd.to_timedelta(rng.integers(0, 3600, n), "s")

    category_mean = {"grocery": 450, "fuel": 700, "fashion": 900, "electronics": 3500,
                     "food_delivery": 220, "airtime_data": 120, "travel": 2800, "education": 1800}
    mean = m["category"].map(category_mean).to_numpy()
    amount = np.round(rng.lognormal(np.log(mean), 0.7), 2)

    channel = rng.choice(["card", "instant_eft", "wallet"], n, p=[0.68, 0.2, 0.12])
    bank = rng.choice(BANKS, n, p=[.24, .22, .2, .16, .12, .06])

    # failure probability depends on channel, bank and time of night
    p_fail = np.where(channel == "card", 0.07, np.where(channel == "instant_eft", 0.11, 0.04))
    p_fail = p_fail + np.where(bank == "Bank F", 0.06, 0) + np.where(hour < 5, 0.04, 0)
    failed = rng.random(n) < p_fail
    reasons = np.where(failed, rng.choice(list(FAILURE_REASONS), n, p=list(FAILURE_REASONS.values())), None)
    # Bank F has more timeouts, a sign of an integration problem
    reasons = np.where(failed & (bank == "Bank F") & (rng.random(n) < 0.5), "timeout", reasons)

    p = pd.DataFrame({
        "payment_id": [f"P{i:06d}" for i in range(n)],
        "merchant_id": m["merchant_id"],
        "created_at": ts,
        "amount": amount,
        "currency": "ZAR",
        "channel": channel,
        "issuing_bank": bank,
        "status": np.where(failed, "failed", "succeeded"),
        "failure_reason": reasons,
    })[keep].reset_index(drop=True)

    # some failed payments are retried by the customer within minutes.
    # A timeout usually goes through on the second try; insufficient funds
    # usually does not.
    retry_rate = {"timeout": 0.7, "3ds_failed": 0.5, "invalid_card": 0.4,
                  "issuer_declined": 0.3, "insufficient_funds": 0.25, "suspected_fraud": 0.15}
    retry_success = {"timeout": 0.85, "3ds_failed": 0.6, "invalid_card": 0.5,
                     "issuer_declined": 0.2, "insufficient_funds": 0.15, "suspected_fraud": 0.1}
    is_failed = p["status"] == "failed"
    p_retry = p["failure_reason"].map(retry_rate).fillna(0).to_numpy()
    retry_src = p[is_failed & (rng.random(len(p)) < p_retry)].copy()
    retry_ok = rng.random(len(retry_src)) < retry_src["failure_reason"].map(retry_success).to_numpy()
    retry_src["payment_id"] = [f"R{i:06d}" for i in range(len(retry_src))]
    retry_src["created_at"] = retry_src["created_at"] + pd.to_timedelta(rng.integers(30, 600, len(retry_src)), "s")
    retry_src["status"] = np.where(retry_ok, "succeeded", "failed")
    retry_src["failure_reason"] = np.where(retry_ok, None, retry_src["failure_reason"])
    p = pd.concat([p, retry_src]).sort_values("created_at").reset_index(drop=True)

    # refunds on a small share of successful payments
    p["refunded"] = (p["status"] == "succeeded") & (rng.random(len(p)) < 0.02)
    return p


def _chargebacks(rng, payments, merchants):
    ok = payments[(payments["status"] == "succeeded") & (payments["channel"] == "card")]
    risky = set(merchants.loc[merchants["high_risk"], "merchant_id"])
    rate = np.where(ok["merchant_id"].isin(risky), 0.025, 0.0035)
    cb = ok[rng.random(len(ok)) < rate].copy()
    cb["chargeback_id"] = [f"CB{i:05d}" for i in range(len(cb))]
    cb["raised_at"] = cb["created_at"] + pd.to_timedelta(rng.integers(3, 60, len(cb)), "D")
    reasons = list(CHARGEBACK_REASONS)
    probs = list(CHARGEBACK_REASONS.values())
    cb["reason"] = rng.choice(reasons, len(cb), p=probs)
    cb.loc[cb["merchant_id"].isin(risky), "reason"] = np.where(
        rng.random(cb["merchant_id"].isin(risky).sum()) < 0.75, "fraud_card_not_present",
        cb.loc[cb["merchant_id"].isin(risky), "reason"])
    # merchants win disputes more often when they have delivery proof
    win_p = np.where(cb["reason"] == "goods_not_received", 0.45,
                     np.where(cb["reason"] == "fraud_card_not_present", 0.15, 0.3))
    cb["outcome"] = np.where(rng.random(len(cb)) < win_p, "merchant_won", "cardholder_won")
    cb = cb[cb["raised_at"] < START + pd.Timedelta(days=DAYS + 30)]
    return cb[["chargeback_id", "payment_id", "merchant_id", "raised_at", "amount",
               "reason", "outcome"]].reset_index(drop=True)


def _settlements(rng, payments, merchants):
    """Bank settlement file: succeeded card and EFT payments, settled T+1,
    gross amount less the merchant discount rate. Then broken on purpose."""
    s = payments[(payments["status"] == "succeeded") & (payments["channel"] != "wallet")].copy()
    s = s.merge(merchants[["merchant_id", "mdr_pct"]], on="merchant_id")
    s["settlement_date"] = (s["created_at"].dt.normalize() + pd.Timedelta(days=1)).dt.date
    s["gross_amount"] = s["amount"]
    s["fee"] = (s["amount"] * s["mdr_pct"] / 100).round(2)
    s["net_amount"] = (s["gross_amount"] - s["fee"]).round(2)
    s["bank_reference"] = [f"BR{i:07d}" for i in range(len(s))]
    s = s[["bank_reference", "payment_id", "merchant_id", "settlement_date",
           "gross_amount", "fee", "net_amount"]].reset_index(drop=True)

    breaks = []
    idx = rng.permutation(len(s))
    cut = np.cumsum([40, 25, 30, 60])
    missing, mismatch, dupes, late = np.split(idx[:cut[-1]], cut[:-1])

    for i in mismatch:
        diff = round(float(rng.choice([-1, 1]) * rng.uniform(0.5, 50)), 2)
        s.loc[i, "gross_amount"] = round(s.loc[i, "gross_amount"] + diff, 2)
        s.loc[i, "net_amount"] = round(s.loc[i, "net_amount"] + diff, 2)
        breaks.append((s.loc[i, "payment_id"], "amount_mismatch"))
    for i in late:
        s.loc[i, "settlement_date"] = s.loc[i, "settlement_date"] + pd.Timedelta(days=int(rng.integers(2, 5)))
        breaks.append((s.loc[i, "payment_id"], "late_settlement"))
    dup_rows = s.loc[dupes].copy()
    dup_rows["bank_reference"] = [f"BD{i:07d}" for i in range(len(dup_rows))]
    breaks += [(pid, "duplicate_in_bank") for pid in dup_rows["payment_id"]]
    breaks += [(pid, "missing_in_bank") for pid in s.loc[missing, "payment_id"]]
    s = s.drop(index=missing)

    # bank lines with no matching payment in our ledger
    unknown = s.sample(15, random_state=SEED).copy()
    unknown["payment_id"] = [f"X{i:06d}" for i in range(len(unknown))]
    unknown["bank_reference"] = [f"BU{i:07d}" for i in range(len(unknown))]
    breaks += [(pid, "missing_in_ledger") for pid in unknown["payment_id"]]

    s = pd.concat([s, dup_rows, unknown]).sort_values("settlement_date").reset_index(drop=True)
    return s, pd.DataFrame(breaks, columns=["payment_id", "break_type"])


def generate(seed=SEED):
    rng = np.random.default_rng(seed)
    merchants = _merchants(rng)
    payments = _payments(rng, merchants)
    chargebacks = _chargebacks(rng, payments, merchants)
    settlements, breaks = _settlements(rng, payments, merchants)
    return {
        "merchants": merchants.drop(columns="high_risk"),
        "payments": payments,
        "settlements": settlements,
        "chargebacks": chargebacks,
        "breaks": breaks,
    }
