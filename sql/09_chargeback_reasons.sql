-- Chargebacks by reason: how often merchants win, and the value lost.
SELECT reason,
       COUNT(*) AS chargebacks,
       ROUND(100.0 * SUM(outcome = 'merchant_won') / COUNT(*), 1) AS merchant_win_rate_pct,
       ROUND(SUM(CASE WHEN outcome = 'cardholder_won' THEN amount ELSE 0 END), 2) AS value_lost
FROM chargebacks
GROUP BY reason
ORDER BY value_lost DESC;
