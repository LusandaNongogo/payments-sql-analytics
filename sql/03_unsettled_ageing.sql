-- Payments still missing from the bank file, aged from the payment date to
-- the last settlement date in the file. Older items carry more risk.
WITH as_of AS (SELECT MAX(settlement_date) AS d FROM settlements),
aged AS (
    SELECT e.payment_id, e.ledger_amount,
           CAST(julianday((SELECT d FROM as_of)) - julianday(e.payment_date) AS INTEGER) AS age_days
    FROM v_recon_exceptions e
    WHERE e.exception_type = 'missing_in_bank'
)
SELECT CASE WHEN age_days <= 7 THEN '1: 0 to 7 days'
            WHEN age_days <= 30 THEN '2: 8 to 30 days'
            WHEN age_days <= 60 THEN '3: 31 to 60 days'
            ELSE '4: over 60 days' END AS age_bucket,
       COUNT(*) AS payments,
       ROUND(SUM(ledger_amount), 2) AS value
FROM aged
GROUP BY age_bucket
ORDER BY age_bucket;
