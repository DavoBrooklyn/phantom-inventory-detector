# Phantom Inventory & Lost Sales Detector

An end-to-end SQLite and Python project that reconciles inventory movements against daily stock snapshots, detects phantom inventory, groups stockout periods, evaluates suppliers, and estimates lost revenue.

## Business Problem

A retailer's system can show stock as available while the product is physically unavailable. This creates cancelled orders, inaccurate reports, emergency stock corrections, and lost sales.

The project answers:

1. Which branch-product-day stock balances do not reconcile?
2. Where does recorded inventory exist but customers cannot buy the product?
3. How much revenue and gross profit may have been lost?
4. Which branches and suppliers create the most inventory risk?

## Stack

- SQLite
- Python
- pandas
- NumPy
- Matplotlib

## Fictional Dataset

- 12 branches
- 60 products
- 6 suppliers
- 90 days
- 64,800 daily inventory snapshots
- Sales, deliveries, waste, corrections, and cancellations
- 160 deliberately inserted problems

No real business data is included.

## Main SQL Work

- Conditional aggregation for daily stock movements
- `LAG()` for previous closing stock
- `ROW_NUMBER()` for duplicate detection
- Gaps-and-islands analysis for consecutive stockouts
- Correlated subqueries for same-weekday demand estimates
- Supplier fill-rate and on-time-delivery calculations
- Branch risk ranking with `RANK()`

## Inventory Equation

```text
Expected closing stock
=
Previous recorded closing stock
+ inflows
- outflows
```

## Run

On Windows, double-click:

```text
run_project.bat
```

Or run:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_all.py
```

## Main Views

- `vw_inventory_reconciliation`
- `vw_reconciliation_issues`
- `vw_duplicate_movements`
- `vw_phantom_inventory`
- `vw_stockout_periods`
- `vw_lost_sales_estimate`
- `vw_supplier_performance`
- `vw_branch_inventory_health`

## Limitations

Lost sales are estimated using the previous four matching weekdays. The classifications are rule-based and should support manual investigation rather than replace it.

## AI Assistance

AI tools assisted with code generation and documentation. The business requirements, analytical logic, validation, testing, and interpretation were directed and reviewed by the project owner.

## License

MIT
