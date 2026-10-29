-- Failure rate by hour of day.
SELECT CAST(strftime('%H', created_at) AS INTEGER) AS hour,
       COUNT(*) AS attempts,
       ROUND(100.0 * SUM(status = 'failed') / COUNT(*), 2) AS failure_rate_pct
FROM payments
GROUP BY hour
ORDER BY hour;
