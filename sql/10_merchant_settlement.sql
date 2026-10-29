-- Monthly gross, fees and net settled per merchant from the bank file,
-- with each merchant's running net total across the quarter.
WITH monthly AS (
    SELECT merchant_id,
           strftime('%Y-%m', settlement_date) AS month,
           SUM(gross_amount) AS gross,
           SUM(fee) AS fees,
           SUM(net_amount) AS net
    FROM settlements
    GROUP BY merchant_id, month
)
SELECT mo.merchant_id,
       m.merchant_name,
       mo.month,
       ROUND(mo.gross, 2) AS gross,
       ROUND(mo.fees, 2) AS fees,
       ROUND(mo.net, 2) AS net,
       ROUND(100.0 * mo.fees / mo.gross, 2) AS effective_fee_pct,
       ROUND(SUM(mo.net) OVER (PARTITION BY mo.merchant_id ORDER BY mo.month), 2) AS running_net
FROM monthly mo
JOIN merchants m ON m.merchant_id = mo.merchant_id
ORDER BY mo.merchant_id, mo.month;
