from pathlib import Path
import subprocess
import sys
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"

def ensure_outputs():
    required = [OUTPUT / "branch_inventory_health.csv", OUTPUT / "supplier_performance.csv", OUTPUT / "reconciliation_issues.csv", OUTPUT / "lost_sales_estimate.csv", OUTPUT / "phantom_inventory.csv", OUTPUT / "validation_summary.csv"]
    if not all(p.exists() for p in required):
        subprocess.run([sys.executable, str(ROOT / "run_all.py")], cwd=ROOT, check=True)

@st.cache_data
def load_data():
    ensure_outputs()
    return {
        "branches": pd.read_csv(OUTPUT / "branch_inventory_health.csv"),
        "suppliers": pd.read_csv(OUTPUT / "supplier_performance.csv"),
        "issues": pd.read_csv(OUTPUT / "reconciliation_issues.csv"),
        "lost": pd.read_csv(OUTPUT / "lost_sales_estimate.csv"),
        "phantom": pd.read_csv(OUTPUT / "phantom_inventory.csv"),
        "validation": pd.read_csv(OUTPUT / "validation_summary.csv")
    }

st.set_page_config(page_title="Phantom Inventory Detector", page_icon="📦", layout="wide")
data = load_data()
branches = data["branches"]
suppliers = data["suppliers"]
issues = data["issues"]
lost = data["lost"]
phantom = data["phantom"]
validation = data["validation"]

st.title("Phantom Inventory & Lost Sales Detector")
st.caption("Operational analytics for inventory accuracy, stockout risk, supplier performance and lost-sales estimation")

branch_options = sorted(set(branches["branch_name"].dropna())) if "branch_name" in branches else []
selected_branches = st.sidebar.multiselect("Branches", branch_options, default=branch_options)
severity_options = sorted(set(issues["issue_severity"].dropna())) if "issue_severity" in issues else []
selected_severity = st.sidebar.multiselect("Issue severity", severity_options, default=severity_options)

branch_view = branches[branches["branch_name"].isin(selected_branches)].copy() if selected_branches and "branch_name" in branches else branches.copy()
issue_view = issues[issues["issue_severity"].isin(selected_severity)].copy() if selected_severity and "issue_severity" in issues else issues.copy()

lost_revenue = float(lost["estimated_lost_revenue"].sum()) if "estimated_lost_revenue" in lost else 0
phantom_cases = len(phantom)
issue_count = len(issue_view)
avg_detection = float(validation["detection_rate"].mean()) if "detection_rate" in validation else 0
avg_on_time = float(suppliers["on_time_delivery_rate"].mean()) if "on_time_delivery_rate" in suppliers else 0

a,b,c,d,e = st.columns(5)
a.metric("Inventory issues", f"{issue_count:,}")
b.metric("Phantom cases", f"{phantom_cases:,}")
c.metric("Estimated lost revenue", "$" + format(lost_revenue, ",.0f"))
d.metric("Validation detection", f"{avg_detection:.1f}%")
e.metric("Supplier on-time rate", f"{avg_on_time:.1f}%")

tab1,tab2,tab3,tab4 = st.tabs(["Executive Overview","Root Causes","Suppliers","Investigation"])

with tab1:
    left,right = st.columns(2)
    if {"branch_name","estimated_lost_revenue"}.issubset(branch_view.columns):
        chart = branch_view.sort_values("estimated_lost_revenue", ascending=True)
        left.plotly_chart(px.bar(chart, x="estimated_lost_revenue", y="branch_name", orientation="h", title="Estimated Lost Revenue by Branch"), use_container_width=True)
    if {"category","estimated_lost_revenue"}.issubset(lost.columns):
        cat = lost.groupby("category", as_index=False)["estimated_lost_revenue"].sum().sort_values("estimated_lost_revenue", ascending=False)
        right.plotly_chart(px.bar(cat, x="category", y="estimated_lost_revenue", title="Lost Revenue by Category"), use_container_width=True)
    st.subheader("Branch Risk Ranking")
    cols = [x for x in ["risk_rank","branch_name","reconciliation_issue_count","phantom_inventory_cases","estimated_lost_revenue"] if x in branch_view.columns]
    st.dataframe(branch_view[cols] if cols else branch_view, use_container_width=True, hide_index=True)

with tab2:
    left,right = st.columns(2)
    if "probable_issue" in issue_view:
        causes = issue_view["probable_issue"].value_counts().rename_axis("cause").reset_index(name="issues")
        left.plotly_chart(px.bar(causes.sort_values("issues"), x="issues", y="cause", orientation="h", title="Reconciliation Issues by Root Cause"), use_container_width=True)
    if "issue_severity" in issue_view:
        severity = issue_view["issue_severity"].value_counts().rename_axis("severity").reset_index(name="issues")
        right.plotly_chart(px.pie(severity, values="issues", names="severity", hole=.45, title="Issue Severity Mix"), use_container_width=True)
    st.subheader("Validation")
    st.dataframe(validation, use_container_width=True, hide_index=True)

with tab3:
    left,right = st.columns(2)
    if {"supplier_name","on_time_delivery_rate"}.issubset(suppliers.columns):
        left.plotly_chart(px.bar(suppliers.sort_values("on_time_delivery_rate"), x="on_time_delivery_rate", y="supplier_name", orientation="h", title="Supplier On-Time Delivery"), use_container_width=True)
    if {"supplier_name","fill_rate"}.issubset(suppliers.columns):
        right.plotly_chart(px.bar(suppliers.sort_values("fill_rate"), x="fill_rate", y="supplier_name", orientation="h", title="Supplier Fill Rate"), use_container_width=True)
    st.dataframe(suppliers, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Highest-Value Phantom Inventory Cases")
    show = phantom.copy()
    if "directly_observed_lost_revenue" in show:
        show = show.sort_values("directly_observed_lost_revenue", ascending=False)
    st.dataframe(show.head(100), use_container_width=True, hide_index=True)
    st.subheader("Largest Reconciliation Differences")
    show_issues = issue_view.copy()
    if "stock_difference" in show_issues:
        show_issues["absolute_difference"] = show_issues["stock_difference"].abs()
        show_issues = show_issues.sort_values("absolute_difference", ascending=False)
    st.dataframe(show_issues.head(100), use_container_width=True, hide_index=True)

st.divider()
st.caption("Synthetic portfolio dataset. Lost-sales estimates are decision-support estimates, not measured real-world financial impact.")
