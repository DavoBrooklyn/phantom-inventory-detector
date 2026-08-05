# Learning Guide

## Study Order

1. `sql/01_schema.sql`
2. `src/generate_data.py`
3. `sql/03_analysis_views.sql`
4. `src/build_database.py`
5. `src/run_analysis.py`

## Core Logic

Inflows are initial stock, deliveries, and positive adjustments.

Outflows are sales, waste, and negative adjustments.

`LAG()` retrieves the previous closing stock for the same branch and product.

`ROW_NUMBER()` identifies repeated movements with the same signature.

Consecutive stockout dates are grouped by subtracting a row number from each date.

Lost demand is estimated from the same weekday during the previous four weeks.

## Interview Explanation

I built a movement-level inventory reconciliation model in SQLite and compared it against daily recorded stock snapshots. I used window functions for previous stock values and duplicate detection, gaps-and-islands logic for stockout periods, and historical weekday demand to estimate lost sales. The results were validated against synthetic problems inserted during data generation.

## Questions to Practise

1. Why use the previous recorded snapshot instead of the previous expected balance?
2. What creates a positive stock difference?
3. What creates a negative stock difference?
4. How does phantom inventory differ from a normal stockout?
5. Why use matching weekdays to estimate demand?
6. How does the gaps-and-islands query group consecutive days?
7. What does supplier fill rate measure?
8. Which indexes improve the main queries?
