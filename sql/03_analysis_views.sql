DROP VIEW IF EXISTS vw_data_quality_issues;
DROP VIEW IF EXISTS vw_branch_inventory_health;
DROP VIEW IF EXISTS vw_supplier_performance;
DROP VIEW IF EXISTS vw_lost_sales_estimate;
DROP VIEW IF EXISTS vw_stockout_periods;
DROP VIEW IF EXISTS vw_stockout_days;
DROP VIEW IF EXISTS vw_phantom_inventory;
DROP VIEW IF EXISTS vw_reconciliation_issues;
DROP VIEW IF EXISTS vw_inventory_reconciliation;
DROP VIEW IF EXISTS vw_duplicate_movements;
DROP VIEW IF EXISTS vw_daily_movements;
DROP VIEW IF EXISTS vw_daily_sales;

CREATE VIEW vw_daily_sales AS
SELECT
    branch_id,
    product_id,
    date(sale_time) AS sale_date,
    SUM(quantity) AS units_sold,
    ROUND(SUM(revenue), 2) AS revenue
FROM sales
GROUP BY branch_id, product_id, date(sale_time);

CREATE VIEW vw_daily_movements AS
SELECT
    branch_id,
    product_id,
    date(movement_time) AS movement_date,
    SUM(CASE WHEN movement_type IN ('INITIAL_STOCK', 'DELIVERY', 'POSITIVE_ADJUSTMENT') THEN quantity ELSE 0 END) AS inflow_quantity,
    SUM(CASE WHEN movement_type IN ('SALE', 'WASTE', 'NEGATIVE_ADJUSTMENT') THEN quantity ELSE 0 END) AS outflow_quantity,
    SUM(CASE WHEN movement_type IN ('INITIAL_STOCK', 'DELIVERY', 'POSITIVE_ADJUSTMENT') THEN quantity ELSE -quantity END) AS net_movement
FROM movements
GROUP BY branch_id, product_id, date(movement_time);

CREATE VIEW vw_duplicate_movements AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY branch_id, product_id, movement_time, movement_type, quantity, COALESCE(reference_id, '')
            ORDER BY movement_id
        ) AS duplicate_number
    FROM movements
)
SELECT *
FROM ranked
WHERE duplicate_number > 1;

CREATE VIEW vw_inventory_reconciliation AS
WITH base AS (
    SELECT
        s.snapshot_id,
        s.branch_id,
        b.branch_name,
        s.product_id,
        p.sku,
        p.product_name,
        p.category,
        s.snapshot_date,
        s.recorded_closing_stock,
        LAG(s.recorded_closing_stock) OVER (
            PARTITION BY s.branch_id, s.product_id
            ORDER BY s.snapshot_date
        ) AS previous_recorded_stock
    FROM snapshots s
    JOIN branches b ON b.branch_id = s.branch_id
    JOIN products p ON p.product_id = s.product_id
),
calculated AS (
    SELECT
        base.*,
        COALESCE(dm.inflow_quantity, 0) AS inflow_quantity,
        COALESCE(dm.outflow_quantity, 0) AS outflow_quantity,
        COALESCE(dm.net_movement, 0) AS net_movement,
        CASE
            WHEN previous_recorded_stock IS NULL THEN COALESCE(dm.net_movement, 0)
            ELSE previous_recorded_stock + COALESCE(dm.net_movement, 0)
        END AS expected_closing_stock
    FROM base
    LEFT JOIN vw_daily_movements dm
        ON dm.branch_id = base.branch_id
       AND dm.product_id = base.product_id
       AND dm.movement_date = base.snapshot_date
)
SELECT
    *,
    recorded_closing_stock - expected_closing_stock AS stock_difference,
    CASE
        WHEN recorded_closing_stock = expected_closing_stock THEN 'Reconciled'
        WHEN recorded_closing_stock > expected_closing_stock THEN 'Recorded stock exceeds ledger'
        ELSE 'Ledger exceeds recorded stock'
    END AS reconciliation_status
FROM calculated;

CREATE VIEW vw_reconciliation_issues AS
WITH duplicate_days AS (
    SELECT branch_id, product_id, date(movement_time) AS issue_date, COUNT(*) AS duplicate_count
    FROM vw_duplicate_movements
    GROUP BY branch_id, product_id, date(movement_time)
),
delivery_days AS (
    SELECT branch_id, product_id, actual_delivery_date AS issue_date, COUNT(*) AS delivery_count
    FROM supplier_orders
    GROUP BY branch_id, product_id, actual_delivery_date
)
SELECT
    r.*,
    COALESCE(d.duplicate_count, 0) AS duplicate_movement_count,
    CASE
        WHEN ABS(stock_difference) >= 25 THEN 'Critical'
        WHEN ABS(stock_difference) >= 10 THEN 'High'
        WHEN ABS(stock_difference) >= 5 THEN 'Medium'
        ELSE 'Low'
    END AS issue_severity,
    CASE
        WHEN stock_difference < 0 AND COALESCE(d.duplicate_count, 0) > 0 THEN 'Duplicate inventory movement'
        WHEN stock_difference > 0 AND COALESCE(o.delivery_count, 0) > 0 AND inflow_quantity = 0 THEN 'Missing delivery movement'
        WHEN stock_difference < 0 THEN 'Possible shrinkage or missing outflow'
        WHEN stock_difference > 0 THEN 'Possible unrecorded inflow or count error'
    END AS probable_issue
FROM vw_inventory_reconciliation r
LEFT JOIN duplicate_days d
    ON d.branch_id = r.branch_id
   AND d.product_id = r.product_id
   AND d.issue_date = r.snapshot_date
LEFT JOIN delivery_days o
    ON o.branch_id = r.branch_id
   AND o.product_id = r.product_id
   AND o.issue_date = r.snapshot_date
WHERE stock_difference <> 0;

CREATE VIEW vw_phantom_inventory AS
WITH cancelled AS (
    SELECT
        branch_id,
        product_id,
        date(cancellation_time) AS cancellation_date,
        SUM(requested_quantity) AS cancelled_quantity
    FROM cancellations
    WHERE reason = 'SYSTEM_SHOWED_AVAILABLE'
    GROUP BY branch_id, product_id, date(cancellation_time)
)
SELECT
    s.branch_id,
    b.branch_name,
    s.product_id,
    p.sku,
    p.product_name,
    p.category,
    s.snapshot_date,
    s.recorded_closing_stock,
    c.cancelled_quantity,
    ROUND(c.cancelled_quantity * p.selling_price, 2) AS directly_observed_lost_revenue
FROM snapshots s
JOIN cancelled c
    ON c.branch_id = s.branch_id
   AND c.product_id = s.product_id
   AND c.cancellation_date = s.snapshot_date
JOIN branches b ON b.branch_id = s.branch_id
JOIN products p ON p.product_id = s.product_id
WHERE s.recorded_closing_stock > 0;

CREATE VIEW vw_stockout_days AS
WITH cancelled AS (
    SELECT
        branch_id,
        product_id,
        date(cancellation_time) AS cancellation_date,
        SUM(requested_quantity) AS cancelled_quantity
    FROM cancellations
    GROUP BY branch_id, product_id, date(cancellation_time)
)
SELECT
    s.branch_id,
    b.branch_name,
    s.product_id,
    p.sku,
    p.product_name,
    p.category,
    s.snapshot_date AS stockout_date,
    s.recorded_closing_stock,
    COALESCE(c.cancelled_quantity, 0) AS cancelled_quantity
FROM snapshots s
JOIN branches b ON b.branch_id = s.branch_id
JOIN products p ON p.product_id = s.product_id
LEFT JOIN cancelled c
    ON c.branch_id = s.branch_id
   AND c.product_id = s.product_id
   AND c.cancellation_date = s.snapshot_date
WHERE s.recorded_closing_stock = 0 OR COALESCE(c.cancelled_quantity, 0) > 0;

CREATE VIEW vw_stockout_periods AS
WITH numbered AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY branch_id, product_id ORDER BY stockout_date) AS row_number
    FROM vw_stockout_days
),
grouped AS (
    SELECT
        *,
        date(stockout_date, '-' || row_number || ' day') AS stockout_group
    FROM numbered
)
SELECT
    branch_id,
    branch_name,
    product_id,
    sku,
    product_name,
    category,
    MIN(stockout_date) AS stockout_start,
    MAX(stockout_date) AS stockout_end,
    COUNT(*) AS stockout_days,
    SUM(cancelled_quantity) AS cancelled_quantity
FROM grouped
GROUP BY branch_id, branch_name, product_id, sku, product_name, category, stockout_group;

CREATE VIEW vw_lost_sales_estimate AS
WITH demand AS (
    SELECT
        sd.*,
        COALESCE(ds.units_sold, 0) AS actual_units_sold,
        (
            SELECT AVG(COALESCE(h.units_sold, 0))
            FROM (
                SELECT date(sd.stockout_date, '-7 day') AS comparison_date
                UNION ALL SELECT date(sd.stockout_date, '-14 day')
                UNION ALL SELECT date(sd.stockout_date, '-21 day')
                UNION ALL SELECT date(sd.stockout_date, '-28 day')
            ) dates
            LEFT JOIN vw_daily_sales h
                ON h.branch_id = sd.branch_id
               AND h.product_id = sd.product_id
               AND h.sale_date = dates.comparison_date
        ) AS expected_units
    FROM vw_stockout_days sd
    LEFT JOIN vw_daily_sales ds
        ON ds.branch_id = sd.branch_id
       AND ds.product_id = sd.product_id
       AND ds.sale_date = sd.stockout_date
)
SELECT
    demand.*,
    ROUND(MAX(cancelled_quantity, COALESCE(expected_units, 0) - actual_units_sold, 0), 2) AS estimated_lost_units,
    ROUND(MAX(cancelled_quantity, COALESCE(expected_units, 0) - actual_units_sold, 0) * p.selling_price, 2) AS estimated_lost_revenue,
    ROUND(MAX(cancelled_quantity, COALESCE(expected_units, 0) - actual_units_sold, 0) * (p.selling_price - p.unit_cost), 2) AS estimated_lost_gross_profit
FROM demand
JOIN products p ON p.product_id = demand.product_id;

CREATE VIEW vw_supplier_performance AS
SELECT
    s.supplier_id,
    s.supplier_name,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN actual_delivery_date > expected_delivery_date THEN 1 ELSE 0 END) AS late_orders,
    ROUND(100.0 * SUM(CASE WHEN actual_delivery_date <= expected_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_delivery_rate,
    ROUND(100.0 * SUM(received_quantity) / SUM(ordered_quantity), 2) AS fill_rate,
    ROUND(AVG(julianday(actual_delivery_date) - julianday(expected_delivery_date)), 2) AS average_delay_days
FROM supplier_orders o
JOIN suppliers s ON s.supplier_id = o.supplier_id
GROUP BY s.supplier_id, s.supplier_name;

CREATE VIEW vw_branch_inventory_health AS
WITH reconciliation AS (
    SELECT
        branch_id,
        COUNT(*) AS snapshots,
        SUM(CASE WHEN stock_difference <> 0 THEN 1 ELSE 0 END) AS issue_count,
        SUM(ABS(stock_difference)) AS absolute_stock_difference
    FROM vw_inventory_reconciliation
    GROUP BY branch_id
),
phantom AS (
    SELECT branch_id, COUNT(*) AS phantom_incidents
    FROM vw_phantom_inventory
    GROUP BY branch_id
),
lost AS (
    SELECT
        branch_id,
        SUM(estimated_lost_revenue) AS estimated_lost_revenue,
        SUM(estimated_lost_gross_profit) AS estimated_lost_gross_profit
    FROM vw_lost_sales_estimate
    GROUP BY branch_id
)
SELECT
    b.branch_id,
    b.branch_name,
    b.region,
    r.snapshots,
    r.issue_count,
    ROUND(100.0 * r.issue_count / r.snapshots, 2) AS reconciliation_issue_rate,
    r.absolute_stock_difference,
    COALESCE(p.phantom_incidents, 0) AS phantom_incidents,
    ROUND(COALESCE(l.estimated_lost_revenue, 0), 2) AS estimated_lost_revenue,
    ROUND(COALESCE(l.estimated_lost_gross_profit, 0), 2) AS estimated_lost_gross_profit,
    RANK() OVER (ORDER BY COALESCE(l.estimated_lost_revenue, 0) DESC, r.issue_count DESC) AS risk_rank
FROM branches b
JOIN reconciliation r ON r.branch_id = b.branch_id
LEFT JOIN phantom p ON p.branch_id = b.branch_id
LEFT JOIN lost l ON l.branch_id = b.branch_id;

CREATE VIEW vw_data_quality_issues AS
SELECT
    'Duplicate inventory movement' AS issue_type,
    movement_id AS record_id,
    branch_id,
    product_id,
    date(movement_time) AS issue_date
FROM vw_duplicate_movements

UNION ALL

SELECT
    'Delivered supplier order without movement' AS issue_type,
    supplier_order_id AS record_id,
    branch_id,
    product_id,
    actual_delivery_date AS issue_date
FROM supplier_orders o
WHERE NOT EXISTS (
    SELECT 1
    FROM movements m
    WHERE m.reference_id = 'SUP-' || o.supplier_order_id
      AND m.movement_type = 'DELIVERY'
);
