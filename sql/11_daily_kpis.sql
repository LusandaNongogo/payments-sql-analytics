-- Daily KPIs for the dashboard, with a 7 day moving average of value.
WITH d AS (
    SELECT date(created_at) AS day,
           COUNT(*) AS attempts,
           SUM(status = 'succeeded') AS succeeded,
           SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) AS value
    FROM payments
    GROUP BY day
)
SELECT day,
       attempts,
       succeeded,
       ROUND(100.0 * succeeded / attempts, 2) AS success_rate_pct,
       ROUND(value, 2) AS value,
       ROUND(value / succeeded, 2) AS avg_ticket,
       ROUND(AVG(value) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS value_7d_avg
FROM d
ORDER BY day;
