SELECT probable_issue, issue_severity, COUNT(*) AS issue_count, SUM(ABS(stock_difference)) AS units_affected
FROM vw_reconciliation_issues
GROUP BY probable_issue, issue_severity
ORDER BY issue_count DESC;

SELECT *
FROM vw_phantom_inventory
ORDER BY directly_observed_lost_revenue DESC;

SELECT *
FROM vw_stockout_periods
ORDER BY stockout_days DESC, cancelled_quantity DESC;

SELECT *
FROM vw_supplier_performance
ORDER BY on_time_delivery_rate, fill_rate;

SELECT *
FROM vw_branch_inventory_health
ORDER BY risk_rank;
