-- Full exception list for the operations team, with merchant name and the
-- next action for each type.
SELECT e.exception_type,
       e.payment_id,
       m.merchant_name,
       e.payment_date,
       e.settlement_date,
       e.ledger_amount,
       e.bank_amount,
       ROUND(COALESCE(e.bank_amount, 0) - COALESCE(e.ledger_amount, 0), 2) AS difference,
       CASE e.exception_type
           WHEN 'missing_in_bank'   THEN 'Query the acquirer for the missing settlement'
           WHEN 'missing_in_ledger' THEN 'Trace the payment; possible unrecorded sale or bank error'
           WHEN 'duplicate_in_bank' THEN 'Claim back the duplicate credit before paying the merchant'
           WHEN 'amount_mismatch'   THEN 'Compare authorisation and capture amounts'
           WHEN 'late_settlement'   THEN 'Log against the acquirer service level'
       END AS next_action
FROM v_recon_exceptions e
LEFT JOIN merchants m ON m.merchant_id = e.merchant_id
ORDER BY e.exception_type, e.payment_date;
