-- Failure reasons ranked within each channel.
WITH r AS (
    SELECT channel, failure_reason, COUNT(*) AS failures
    FROM payments
    WHERE status = 'failed'
    GROUP BY channel, failure_reason
)
SELECT channel,
       failure_reason,
       failures,
       ROUND(100.0 * failures / SUM(failures) OVER (PARTITION BY channel), 1) AS share_pct,
       RANK() OVER (PARTITION BY channel ORDER BY failures DESC) AS rank_in_channel
FROM r
ORDER BY channel, rank_in_channel;
