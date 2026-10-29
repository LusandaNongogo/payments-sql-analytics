-- Chargeback rate per merchant on card sales, by count. Merchants above
-- 1% are flagged: card schemes run monitoring programmes at around that
-- level, with fines and possible loss of card acceptance.
WITH sales AS (
    SELECT merchant_id, COUNT(*) AS card_sales, SUM(amount) AS card_value
    FROM payments
    WHERE status = 'succeeded' AND channel = 'card'
    GROUP BY merchant_id
),
cb AS (
    SELECT merchant_id, COUNT(*) AS chargebacks, SUM(amount) AS chargeback_value,
           SUM(reason = 'fraud_card_not_present') AS fraud_chargebacks
    FROM chargebacks
    GROUP BY merchant_id
)
SELECT m.merchant_id,
       m.merchant_name,
       m.category,
       s.card_sales,
       COALESCE(cb.chargebacks, 0) AS chargebacks,
       ROUND(100.0 * COALESCE(cb.chargebacks, 0) / s.card_sales, 2) AS chargeback_rate_pct,
       ROUND(100.0 * COALESCE(cb.fraud_chargebacks, 0) / NULLIF(cb.chargebacks, 0), 0) AS fraud_share_pct,
       CASE WHEN 1.0 * COALESCE(cb.chargebacks, 0) / s.card_sales > 0.01 THEN 'review' ELSE '' END AS flag,
       RANK() OVER (ORDER BY 1.0 * COALESCE(cb.chargebacks, 0) / s.card_sales DESC) AS risk_rank
FROM sales s
JOIN merchants m ON m.merchant_id = s.merchant_id
LEFT JOIN cb ON cb.merchant_id = s.merchant_id
WHERE s.card_sales >= 100
ORDER BY risk_rank
LIMIT 15;
