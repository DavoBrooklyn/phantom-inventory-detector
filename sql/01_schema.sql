PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS cancellations;
DROP TABLE IF EXISTS snapshots;
DROP TABLE IF EXISTS movements;
DROP TABLE IF EXISTS supplier_orders;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS branches;

CREATE TABLE branches (
    branch_id INTEGER PRIMARY KEY,
    branch_name TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL
);

CREATE TABLE suppliers (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    supplier_id INTEGER NOT NULL,
    unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
    selling_price REAL NOT NULL CHECK (selling_price >= unit_cost),
    reorder_point INTEGER NOT NULL CHECK (reorder_point >= 0),
    target_stock INTEGER NOT NULL CHECK (target_stock >= reorder_point),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE sales (
    sale_id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    sale_time TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    revenue REAL NOT NULL CHECK (revenue >= 0),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE supplier_orders (
    supplier_order_id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    expected_delivery_date TEXT NOT NULL,
    actual_delivery_date TEXT NOT NULL,
    ordered_quantity INTEGER NOT NULL CHECK (ordered_quantity > 0),
    received_quantity INTEGER NOT NULL CHECK (received_quantity > 0),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE movements (
    movement_id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    movement_time TEXT NOT NULL,
    movement_type TEXT NOT NULL CHECK (
        movement_type IN ('INITIAL_STOCK', 'DELIVERY', 'SALE', 'WASTE', 'POSITIVE_ADJUSTMENT', 'NEGATIVE_ADJUSTMENT')
    ),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    reference_id TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE snapshots (
    snapshot_id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    recorded_closing_stock INTEGER NOT NULL,
    UNIQUE (branch_id, product_id, snapshot_date),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE cancellations (
    cancellation_id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    cancellation_time TEXT NOT NULL,
    requested_quantity INTEGER NOT NULL CHECK (requested_quantity > 0),
    reason TEXT NOT NULL CHECK (reason IN ('OUT_OF_STOCK', 'SYSTEM_SHOWED_AVAILABLE')),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
