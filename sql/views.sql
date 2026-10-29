-- Shared views used by the analysis queries.

-- Payments the bank should settle: succeeded card and instant EFT.
-- Wallet payments settle internally and never appear in the bank file.
DROP VIEW IF EXISTS v_settleable;
CREATE VIEW v_settleable AS
SELECT payment_id, merchant_id, created_at, date(created_at) AS payment_date, amount
FROM payments
WHERE status = 'succeeded'
  AND channel IN ('card', 'instant_eft');

-- Every reconciliation exception between our ledger and the bank file,
-- one row per exception.
DROP VIEW IF EXISTS v_recon_exceptions;
CREATE VIEW v_recon_exceptions AS
WITH bank AS (
    SELECT s.*,
           COUNT(*) OVER (PARTITION BY payment_id) AS lines_for_payment,
           ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY bank_reference) AS line_no
    FROM settlements s
)
-- in our ledger, not in the bank file
SELECT l.payment_id, l.merchant_id, l.payment_date, NULL AS settlement_date,
       l.amount AS ledger_amount, NULL AS bank_amount,
       'missing_in_bank' AS exception_type
FROM v_settleable l
LEFT JOIN bank b ON b.payment_id = l.payment_id
WHERE b.payment_id IS NULL

UNION ALL
-- in the bank file, not in our ledger
SELECT b.payment_id, b.merchant_id, NULL, b.settlement_date,
       NULL, b.gross_amount, 'missing_in_ledger'
FROM bank b
LEFT JOIN payments p ON p.payment_id = b.payment_id
WHERE p.payment_id IS NULL

UNION ALL
-- the same payment settled more than once
SELECT b.payment_id, b.merchant_id, l.payment_date, b.settlement_date,
       l.amount, b.gross_amount, 'duplicate_in_bank'
FROM bank b
JOIN v_settleable l ON l.payment_id = b.payment_id
WHERE b.lines_for_payment > 1 AND b.line_no > 1

UNION ALL
-- amounts differ by more than half a cent
SELECT b.payment_id, b.merchant_id, l.payment_date, b.settlement_date,
       l.amount, b.gross_amount, 'amount_mismatch'
FROM bank b
JOIN v_settleable l ON l.payment_id = b.payment_id
WHERE b.line_no = 1 AND ABS(b.gross_amount - l.amount) > 0.005

UNION ALL
-- settled later than T+1
SELECT b.payment_id, b.merchant_id, l.payment_date, b.settlement_date,
       l.amount, b.gross_amount, 'late_settlement'
FROM bank b
JOIN v_settleable l ON l.payment_id = b.payment_id
WHERE b.line_no = 1
  AND julianday(b.settlement_date) - julianday(l.payment_date) > 1;
