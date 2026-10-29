-- Failure rate by channel and issuing bank, and how much of each bank's
-- failures are timeouts (a technical problem) rather than declines.
SELECT channel,
       issuing_bank,
       COUNT(*) AS attempts,
       SUM(status = 'failed') AS failed,
       ROUND(100.0 * SUM(status = 'failed') / COUNT(*), 2) AS failure_rate_pct,
       ROUND(100.0 * SUM(failure_reason = 'timeout') / NULLIF(SUM(status = 'failed'), 0), 1) AS timeout_share_pct
FROM payments
GROUP BY channel, issuing_bank
ORDER BY channel, failure_rate_pct DESC;
