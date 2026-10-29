-- Month on month growth in successful payment value per merchant category.
WITH m AS (
    SELECT mc.category,
           strftime('%Y-%m', p.created_at) AS month,
           SUM(p.amount) AS value
    FROM payments p
    JOIN merchants mc ON mc.merchant_id = p.merchant_id
    WHERE p.status = 'succeeded'
    GROUP BY mc.category, month
)
SELECT category,
       month,
       ROUND(value, 2) AS value,
       ROUND(LAG(value) OVER (PARTITION BY category ORDER BY month), 2) AS prior_month,
       ROUND(100.0 * (value - LAG(value) OVER (PARTITION BY category ORDER BY month))
             / LAG(value) OVER (PARTITION BY category ORDER BY month), 1) AS growth_pct
FROM m
ORDER BY category, month;
