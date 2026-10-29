-- Payments data model. One ledger table (payments) at the centre, with the
-- bank's settlement file and chargebacks joining back to it on payment_id.

CREATE TABLE merchants (
    merchant_id    TEXT PRIMARY KEY,
    merchant_name  TEXT NOT NULL,
    category       TEXT NOT NULL,
    province       TEXT NOT NULL,
    mdr_pct        REAL NOT NULL,   -- merchant discount rate, % of gross
    onboarded      TEXT NOT NULL
);

CREATE TABLE payments (
    payment_id      TEXT PRIMARY KEY,
    merchant_id     TEXT NOT NULL REFERENCES merchants (merchant_id),
    created_at      TEXT NOT NULL,
    amount          REAL NOT NULL,
    currency        TEXT NOT NULL,
    channel         TEXT NOT NULL,   -- card, instant_eft, wallet
    issuing_bank    TEXT NOT NULL,
    status          TEXT NOT NULL,   -- succeeded, failed
    failure_reason  TEXT,
    refunded        INTEGER NOT NULL
);

-- the acquiring bank's file: no primary key on payment_id on purpose,
-- because real files can contain duplicates
CREATE TABLE settlements (
    bank_reference   TEXT PRIMARY KEY,
    payment_id       TEXT NOT NULL,
    merchant_id      TEXT NOT NULL,
    settlement_date  TEXT NOT NULL,
    gross_amount     REAL NOT NULL,
    fee              REAL NOT NULL,
    net_amount       REAL NOT NULL
);

CREATE TABLE chargebacks (
    chargeback_id  TEXT PRIMARY KEY,
    payment_id     TEXT NOT NULL REFERENCES payments (payment_id),
    merchant_id    TEXT NOT NULL REFERENCES merchants (merchant_id),
    raised_at      TEXT NOT NULL,
    amount         REAL NOT NULL,
    reason         TEXT NOT NULL,
    outcome        TEXT NOT NULL
);

-- answer key for the planted reconciliation breaks, used by the tests only
CREATE TABLE breaks (
    payment_id  TEXT NOT NULL,
    break_type  TEXT NOT NULL
);

CREATE INDEX ix_payments_merchant ON payments (merchant_id);
CREATE INDEX ix_payments_created ON payments (created_at);
CREATE INDEX ix_settlements_payment ON settlements (payment_id);
CREATE INDEX ix_chargebacks_payment ON chargebacks (payment_id);
