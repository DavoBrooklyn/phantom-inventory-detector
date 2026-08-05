CREATE INDEX idx_sales_lookup ON sales(branch_id, product_id, sale_time);
CREATE INDEX idx_movements_lookup ON movements(branch_id, product_id, movement_time);
CREATE INDEX idx_snapshots_lookup ON snapshots(branch_id, product_id, snapshot_date);
CREATE INDEX idx_orders_lookup ON supplier_orders(branch_id, product_id, actual_delivery_date);
CREATE INDEX idx_cancellations_lookup ON cancellations(branch_id, product_id, cancellation_time);
CREATE INDEX idx_movement_reference ON movements(reference_id);
