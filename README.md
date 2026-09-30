# Phantom Inventory & Lost Sales Detector

An end-to-end inventory analytics project built with SQLite, SQL, Python and Streamlit. It reconciles stock movements against daily snapshots, detects phantom inventory, identifies operational root causes, estimates lost sales, evaluates suppliers and ranks branch inventory risk.

## Business Problem

Inventory systems can report stock as available even when customers cannot actually buy the product. That creates cancellations, inaccurate replenishment decisions, emergency corrections and lost revenue.

The project answers which balances fail to reconcile, where phantom inventory appears, which branches and categories create the most risk, and which suppliers contribute to availability problems.

## Analytical Pipeline

Synthetic operational data → SQLite relational model → SQL reconciliation and diagnostic views → Python validation and reporting → interactive Streamlit dashboard → operational decisions.

## Stack

SQLite, SQL, Python, pandas, NumPy, Plotly, Streamlit and Matplotlib.

## Dataset

The reproducible synthetic dataset contains 12 branches, 60 products, 6 suppliers, 90 days of inventory history and 64,800 daily inventory snapshots. It includes sales, deliveries, waste, corrections and cancellations, plus deliberately inserted inventory problems for validation.

## SQL Techniques

The SQL layer uses conditional aggregation, CTEs, LAG(), ROW_NUMBER(), RANK(), gaps-and-islands logic, correlated subqueries and multi-table reconciliation.

Core views: vw_inventory_reconciliation, vw_reconciliation_issues, vw_duplicate_movements, vw_phantom_inventory, vw_stockout_periods, vw_lost_sales_estimate, vw_supplier_performance and vw_branch_inventory_health.

## Dashboard

The Streamlit dashboard contains Executive Overview, Root Causes, Suppliers and Investigation views. It exposes inventory issues, phantom cases, estimated lost revenue, validation performance, branch risk, root causes, supplier metrics and detailed investigation records.

## Inventory Logic

Expected closing stock = previous recorded closing stock + inflows - outflows.

A difference between expected and recorded stock becomes an investigation candidate. Additional rules distinguish likely duplicate movements, missing outflows, phantom inventory and other operational issues.

## Lost Sales

Lost sales are estimated from recent matching weekdays rather than treated as known revenue. The result is a prioritization metric, not a claim of measured real-world financial impact.

## Run

On Windows, double-click start_dashboard.bat.

Or run:

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_all.py
streamlit run dashboard/app.py

The dashboard automatically builds the project outputs if they are missing.

## Business Use

The analysis supports cycle-count prioritization, branch investigation, supplier review, stockout reduction and inventory-control decisions. The dataset is synthetic and reproducible.
