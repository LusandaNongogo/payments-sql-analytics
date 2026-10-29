-- How many failed payments the customer retried successfully within 15
-- minutes (same merchant, amount and bank), by failure reason. Recovered
-- value is revenue that a smarter retry or better error message could
-- protect; unrecovered value is lost sales.
WITH failed AS (
    SELECT payment_id, merchant_id, amount, issuing_bank, created_at, failure_reason
    FROM payments
    WHERE status = 'failed'
),
recovered AS (
    SELECT DISTINCT f.payment_id
    FROM failed f
    JOIN payments r
      ON r.merchant_id = f.merchant_id
     AND r.amount = f.amount
     AND r.issuing_bank = f.issuing_bank
     AND r.status = 'succeeded'
     AND r.created_at > f.created_at
     AND (julianday(r.created_at) - julianday(f.created_at)) * 24 * 60 <= 15
)
SELECT f.failure_reason,
       COUNT(*) AS failed_payments,
       SUM(rc.payment_id IS NOT NULL) AS recovered_by_retry,
       ROUND(100.0 * SUM(rc.payment_id IS NOT NULL) / COUNT(*), 1) AS recovery_rate_pct,
       ROUND(SUM(CASE WHEN rc.payment_id IS NULL THEN f.amount ELSE 0 END), 2) AS unrecovered_value
FROM failed f
LEFT JOIN recovered rc ON rc.payment_id = f.payment_id
GROUP BY f.failure_reason
ORDER BY unrecovered_value DESC;
