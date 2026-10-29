-- Reconciliation exceptions by type, with the value at stake.
-- For a mismatch the value is the difference; for the rest it is the full amount.
SELECT exception_type,
       COUNT(*) AS exceptions,
       ROUND(SUM(CASE exception_type
                     WHEN 'amount_mismatch' THEN ABS(bank_amount - ledger_amount)
                     WHEN 'missing_in_ledger' THEN bank_amount
                     WHEN 'duplicate_in_bank' THEN bank_amount
                     ELSE ledger_amount END), 2) AS value_at_stake
FROM v_recon_exceptions
GROUP BY exception_type
ORDER BY value_at_stake DESC;
