import shutil
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from src.config import DATABASE_PATH, OUTPUT_DIR, OUTPUT_CHART_DIR, DOCS_CHART_DIR, DOCS_RESULT_DIR, VALIDATION_DIR

EXPORTS = {
    'inventory_reconciliation.csv': 'SELECT * FROM vw_inventory_reconciliation',
    'reconciliation_issues.csv': 'SELECT * FROM vw_reconciliation_issues ORDER BY ABS(stock_difference) DESC',
    'phantom_inventory.csv': 'SELECT * FROM vw_phantom_inventory ORDER BY directly_observed_lost_revenue DESC',
    'stockout_periods.csv': 'SELECT * FROM vw_stockout_periods ORDER BY stockout_days DESC',
    'lost_sales_estimate.csv': 'SELECT * FROM vw_lost_sales_estimate ORDER BY estimated_lost_revenue DESC',
    'supplier_performance.csv': 'SELECT * FROM vw_supplier_performance ORDER BY on_time_delivery_rate',
    'branch_inventory_health.csv': 'SELECT * FROM vw_branch_inventory_health ORDER BY risk_rank',
    'data_quality_issues.csv': 'SELECT * FROM vw_data_quality_issues'
}


def validate(connection):
    known = pd.read_csv(VALIDATION_DIR / 'known_issues.csv')
    queries = {
        'Phantom inventory': 'SELECT branch_id, product_id, snapshot_date AS issue_date FROM vw_phantom_inventory',
        'Duplicate inventory movement': 'SELECT branch_id, product_id, date(movement_time) AS issue_date FROM vw_duplicate_movements',
        'Missing delivery movement': "SELECT branch_id, product_id, actual_delivery_date AS issue_date FROM supplier_orders o WHERE NOT EXISTS (SELECT 1 FROM movements m WHERE m.reference_id = 'SUP-' || o.supplier_order_id AND m.movement_type = 'DELIVERY')",
        'Possible shrinkage or missing outflow': "SELECT branch_id, product_id, snapshot_date AS issue_date FROM vw_reconciliation_issues WHERE probable_issue = 'Possible shrinkage or missing outflow'"
    }
    detected = []
    for issue_type, query in queries.items():
        frame = pd.read_sql_query(query, connection)
        frame['issue_type'] = issue_type
        detected.append(frame[['issue_type', 'branch_id', 'product_id', 'issue_date']])
    detected = pd.concat(detected, ignore_index=True).drop_duplicates()
    merged = known.merge(detected, on=['issue_type', 'branch_id', 'product_id', 'issue_date'], how='left', indicator=True)
    merged['detected'] = (merged['_merge'] == 'both').astype(int)
    result = merged.groupby('issue_type', as_index=False).agg(expected_issues=('issue_date', 'count'), detected_issues=('detected', 'sum'))
    result['detection_rate'] = (100 * result.detected_issues / result.expected_issues).round(2)
    result.to_csv(OUTPUT_DIR / 'validation_summary.csv', index=False)
    return result


def create_charts(connection):
    branch = pd.read_sql_query('SELECT branch_name, estimated_lost_revenue FROM vw_branch_inventory_health ORDER BY risk_rank LIMIT 10', connection)
    supplier = pd.read_sql_query('SELECT supplier_name, on_time_delivery_rate FROM vw_supplier_performance ORDER BY on_time_delivery_rate', connection)
    causes = pd.read_sql_query('SELECT probable_issue, COUNT(*) issue_count FROM vw_reconciliation_issues GROUP BY probable_issue ORDER BY issue_count DESC', connection)
    category = pd.read_sql_query('SELECT category, ROUND(SUM(estimated_lost_revenue), 2) estimated_lost_revenue FROM vw_lost_sales_estimate GROUP BY category ORDER BY estimated_lost_revenue DESC', connection)

    plt.figure(figsize=(10, 6))
    plt.barh(branch.branch_name[::-1], branch.estimated_lost_revenue[::-1])
    plt.xlabel('Estimated Lost Revenue')
    plt.title('Branches with the Highest Estimated Lost Revenue')
    plt.tight_layout()
    plt.savefig(OUTPUT_CHART_DIR / 'branch_lost_revenue.png', dpi=160)
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.bar(supplier.supplier_name, supplier.on_time_delivery_rate)
    plt.ylabel('On-Time Delivery Rate (%)')
    plt.title('Supplier Delivery Performance')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(OUTPUT_CHART_DIR / 'supplier_performance.png', dpi=160)
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.barh(causes.probable_issue[::-1], causes.issue_count[::-1])
    plt.xlabel('Issue Count')
    plt.title('Inventory Reconciliation Issue Causes')
    plt.tight_layout()
    plt.savefig(OUTPUT_CHART_DIR / 'issue_causes.png', dpi=160)
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.bar(category.category, category.estimated_lost_revenue)
    plt.ylabel('Estimated Lost Revenue')
    plt.title('Estimated Lost Revenue by Category')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(OUTPUT_CHART_DIR / 'category_lost_revenue.png', dpi=160)
    plt.close()

    for chart in OUTPUT_CHART_DIR.glob('*.png'):
        shutil.copy2(chart, DOCS_CHART_DIR / chart.name)


def create_html(connection, validation):
    summary = pd.read_sql_query("SELECT (SELECT COUNT(*) FROM snapshots) snapshots, (SELECT COUNT(*) FROM vw_reconciliation_issues) issues, (SELECT COUNT(*) FROM vw_phantom_inventory) phantom, (SELECT COUNT(*) FROM vw_duplicate_movements) duplicates, (SELECT ROUND(SUM(estimated_lost_revenue), 2) FROM vw_lost_sales_estimate) lost_revenue", connection).iloc[0]
    branches = pd.read_sql_query('SELECT * FROM vw_branch_inventory_health ORDER BY risk_rank LIMIT 10', connection)
    suppliers = pd.read_sql_query('SELECT * FROM vw_supplier_performance ORDER BY on_time_delivery_rate', connection)
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Phantom Inventory Report</title><style>body{{font-family:Arial;max-width:1150px;margin:40px auto;padding:0 20px}}.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}.card{{border:1px solid #ccc;border-radius:8px;padding:15px}}.value{{font-size:25px;font-weight:bold}}table{{border-collapse:collapse;width:100%;margin:20px 0}}th,td{{border:1px solid #ccc;padding:7px}}img{{max-width:900px;width:100%}}</style></head><body><h1>Phantom Inventory & Lost Sales Detector</h1><div class="cards"><div class="card">Snapshots<div class="value">{int(summary.snapshots):,}</div></div><div class="card">Issues<div class="value">{int(summary.issues):,}</div></div><div class="card">Phantom cases<div class="value">{int(summary.phantom):,}</div></div><div class="card">Duplicates<div class="value">{int(summary.duplicates):,}</div></div><div class="card">Lost revenue<div class="value">${float(summary.lost_revenue or 0):,.2f}</div></div></div><h2>Highest-Risk Branches</h2>{branches.to_html(index=False)}<h2>Supplier Performance</h2>{suppliers.to_html(index=False)}<h2>Validation</h2>{validation.to_html(index=False)}<h2>Charts</h2><img src="charts/branch_lost_revenue.png"><img src="charts/supplier_performance.png"><img src="charts/issue_causes.png"><img src="charts/category_lost_revenue.png"></body></html>'''
    (OUTPUT_DIR / 'executive_report.html').write_text(html, encoding='utf-8')


def run_analysis():
    connection = sqlite3.connect(DATABASE_PATH)
    for file_name, query in EXPORTS.items():
        frame = pd.read_sql_query(query, connection)
        frame.to_csv(OUTPUT_DIR / file_name, index=False)
        print(f'Exported {file_name} with {len(frame):,} rows')
    validation = validate(connection)
    create_charts(connection)
    pd.read_sql_query('SELECT * FROM vw_branch_inventory_health ORDER BY risk_rank LIMIT 12', connection).to_csv(DOCS_RESULT_DIR / 'branch_inventory_health.csv', index=False)
    pd.read_sql_query('SELECT * FROM vw_supplier_performance ORDER BY on_time_delivery_rate', connection).to_csv(DOCS_RESULT_DIR / 'supplier_performance.csv', index=False)
    pd.read_sql_query('SELECT * FROM vw_phantom_inventory ORDER BY directly_observed_lost_revenue DESC LIMIT 20', connection).to_csv(DOCS_RESULT_DIR / 'phantom_inventory_examples.csv', index=False)
    validation.to_csv(DOCS_RESULT_DIR / 'validation_summary.csv', index=False)
    create_html(connection, validation)
    connection.close()
    print()
    print(validation.to_string(index=False))
    print(f'Reports created in {OUTPUT_DIR}')


if __name__ == '__main__':
    run_analysis()
