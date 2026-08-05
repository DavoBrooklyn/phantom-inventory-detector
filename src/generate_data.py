from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from src.config import RAW_DIR, VALIDATION_DIR, SEED


def choose_anomalies(rng, branches, products, days):
    keys = [(b, p, d) for b in range(1, branches + 1) for p in range(1, products + 1) for d in range(2, days - 2)]
    chosen = rng.choice(len(keys), size=160, replace=False)
    names = [('phantom', 45), ('shrinkage', 45), ('missing_delivery', 35), ('duplicate_delivery', 35)]
    result = {}
    offset = 0
    for name, count in names:
        result[name] = {keys[int(i)] for i in chosen[offset:offset + count]}
        offset += count
    return result


def generate_all():
    rng = np.random.default_rng(SEED)
    start = datetime(2025, 1, 1)
    branch_count = 12
    product_count = 60
    supplier_count = 6
    days = 90

    branches = pd.DataFrame({
        'branch_id': range(1, branch_count + 1),
        'branch_name': [f'UrbanMart Branch {i:02d}' for i in range(1, branch_count + 1)],
        'region': [['Central', 'North', 'South', 'East'][(i - 1) % 4] for i in range(1, branch_count + 1)]
    })
    suppliers = pd.DataFrame({
        'supplier_id': range(1, supplier_count + 1),
        'supplier_name': [f'Supplier {i:02d}' for i in range(1, supplier_count + 1)]
    })

    categories = ['Beverages', 'Snacks', 'Dairy', 'Bakery', 'Frozen', 'Household']
    products = []
    for product_id in range(1, product_count + 1):
        cost = round(float(rng.uniform(0.8, 12.0)), 2)
        reorder = int(rng.integers(7, 20))
        category = categories[(product_id - 1) % len(categories)]
        products.append({
            'product_id': product_id,
            'sku': f'SKU-{product_id:04d}',
            'product_name': f'{category} Product {product_id:03d}',
            'category': category,
            'supplier_id': ((product_id - 1) % supplier_count) + 1,
            'unit_cost': cost,
            'selling_price': round(cost * float(rng.uniform(1.35, 1.95)), 2),
            'reorder_point': reorder,
            'target_stock': reorder + int(rng.integers(25, 50))
        })
    products = pd.DataFrame(products)
    anomalies = choose_anomalies(rng, branch_count, product_count, days)

    sales = []
    orders = []
    movements = []
    snapshots = []
    cancellations = []
    validation = []
    sale_id = order_id = movement_id = snapshot_id = cancellation_id = 1

    for branch_id in range(1, branch_count + 1):
        branch_factor = float(rng.uniform(0.85, 1.25))
        for product_id in range(1, product_count + 1):
            product = products.iloc[product_id - 1]
            stock = int(product.target_stock) + int(rng.integers(5, 16))
            demand_base = float(rng.uniform(1.0, 4.5)) * branch_factor
            deliveries = defaultdict(list)
            phantom_correction = 0

            movements.append({
                'movement_id': movement_id,
                'branch_id': branch_id,
                'product_id': product_id,
                'movement_time': start.replace(hour=6).strftime('%Y-%m-%d %H:%M:%S'),
                'movement_type': 'INITIAL_STOCK',
                'quantity': stock,
                'reference_id': f'INIT-{branch_id}-{product_id}'
            })
            movement_id += 1

            for day in range(days):
                current = start + timedelta(days=day)
                date_text = current.strftime('%Y-%m-%d')
                key = (branch_id, product_id, day)

                if phantom_correction:
                    movements.append({
                        'movement_id': movement_id,
                        'branch_id': branch_id,
                        'product_id': product_id,
                        'movement_time': current.replace(hour=6, minute=10).strftime('%Y-%m-%d %H:%M:%S'),
                        'movement_type': 'NEGATIVE_ADJUSTMENT',
                        'quantity': phantom_correction,
                        'reference_id': f'PHANTOM-CORRECTION-{branch_id}-{product_id}-{day}'
                    })
                    movement_id += 1
                    phantom_correction = 0

                for delivery in deliveries.pop(day, []):
                    stock += delivery['quantity']
                    movements.append({
                        'movement_id': movement_id,
                        'branch_id': branch_id,
                        'product_id': product_id,
                        'movement_time': current.replace(hour=7, minute=20).strftime('%Y-%m-%d %H:%M:%S'),
                        'movement_type': 'DELIVERY',
                        'quantity': delivery['quantity'],
                        'reference_id': f"SUP-{delivery['order_id']}"
                    })
                    movement_id += 1

                if stock <= int(product.reorder_point) and not deliveries:
                    delay = int(rng.choice([0, 0, 0, 1, 1, 2]))
                    ordered = int(product.target_stock) - stock + int(rng.integers(5, 15))
                    received = max(1, int(round(ordered * float(rng.choice([1.0, 1.0, 0.9, 0.8])))))
                    delivery_day = min(day + delay, days - 1)
                    orders.append({
                        'supplier_order_id': order_id,
                        'branch_id': branch_id,
                        'product_id': product_id,
                        'supplier_id': int(product.supplier_id),
                        'order_date': date_text,
                        'expected_delivery_date': date_text,
                        'actual_delivery_date': (start + timedelta(days=delivery_day)).strftime('%Y-%m-%d'),
                        'ordered_quantity': ordered,
                        'received_quantity': received
                    })
                    if delivery_day == day:
                        stock += received
                        movements.append({
                            'movement_id': movement_id,
                            'branch_id': branch_id,
                            'product_id': product_id,
                            'movement_time': current.replace(hour=7, minute=20).strftime('%Y-%m-%d %H:%M:%S'),
                            'movement_type': 'DELIVERY',
                            'quantity': received,
                            'reference_id': f'SUP-{order_id}'
                        })
                        movement_id += 1
                    else:
                        deliveries[delivery_day].append({'order_id': order_id, 'quantity': received})
                    order_id += 1

                if key in anomalies['missing_delivery'] or key in anomalies['duplicate_delivery']:
                    quantity = int(rng.integers(12, 28))
                    orders.append({
                        'supplier_order_id': order_id,
                        'branch_id': branch_id,
                        'product_id': product_id,
                        'supplier_id': int(product.supplier_id),
                        'order_date': (current - timedelta(days=1)).strftime('%Y-%m-%d'),
                        'expected_delivery_date': date_text,
                        'actual_delivery_date': date_text,
                        'ordered_quantity': quantity,
                        'received_quantity': quantity
                    })
                    stock += quantity
                    if key in anomalies['missing_delivery']:
                        validation.append({'issue_type': 'Missing delivery movement', 'branch_id': branch_id, 'product_id': product_id, 'issue_date': date_text})
                    else:
                        delivery_time = current.replace(hour=7, minute=35).strftime('%Y-%m-%d %H:%M:%S')
                        for _ in range(2):
                            movements.append({
                                'movement_id': movement_id,
                                'branch_id': branch_id,
                                'product_id': product_id,
                                'movement_time': delivery_time,
                                'movement_type': 'DELIVERY',
                                'quantity': quantity,
                                'reference_id': f'SUP-{order_id}'
                            })
                            movement_id += 1
                        validation.append({'issue_type': 'Duplicate inventory movement', 'branch_id': branch_id, 'product_id': product_id, 'issue_date': date_text})
                    order_id += 1

                demand = int(rng.poisson(max(0.1, demand_base * (1.2 if current.weekday() in (4, 5) else 1.0))))
                sold = min(demand, stock)
                if sold:
                    sale_time = current.replace(hour=int(rng.integers(9, 21)), minute=int(rng.integers(0, 60)))
                    revenue = round(sold * float(product.selling_price), 2)
                    sales.append({'sale_id': sale_id, 'branch_id': branch_id, 'product_id': product_id, 'sale_time': sale_time.strftime('%Y-%m-%d %H:%M:%S'), 'quantity': sold, 'revenue': revenue})
                    movements.append({'movement_id': movement_id, 'branch_id': branch_id, 'product_id': product_id, 'movement_time': sale_time.strftime('%Y-%m-%d %H:%M:%S'), 'movement_type': 'SALE', 'quantity': sold, 'reference_id': f'SALE-{sale_id}'})
                    sale_id += 1
                    movement_id += 1
                    stock -= sold

                unmet = max(demand - sold, 0)
                if unmet:
                    cancellations.append({'cancellation_id': cancellation_id, 'branch_id': branch_id, 'product_id': product_id, 'cancellation_time': current.replace(hour=18).strftime('%Y-%m-%d %H:%M:%S'), 'requested_quantity': unmet, 'reason': 'OUT_OF_STOCK'})
                    cancellation_id += 1

                if rng.random() < 0.01 and stock > 2:
                    waste = int(rng.integers(1, min(4, stock) + 1))
                    stock -= waste
                    movements.append({'movement_id': movement_id, 'branch_id': branch_id, 'product_id': product_id, 'movement_time': current.replace(hour=20).strftime('%Y-%m-%d %H:%M:%S'), 'movement_type': 'WASTE', 'quantity': waste, 'reference_id': f'WASTE-{branch_id}-{product_id}-{day}'})
                    movement_id += 1

                if key in anomalies['shrinkage']:
                    if stock < 12:
                        stock += 20
                        movements.append({'movement_id': movement_id, 'branch_id': branch_id, 'product_id': product_id, 'movement_time': current.replace(hour=20, minute=20).strftime('%Y-%m-%d %H:%M:%S'), 'movement_type': 'POSITIVE_ADJUSTMENT', 'quantity': 20, 'reference_id': f'COUNT-{branch_id}-{product_id}-{day}'})
                        movement_id += 1
                    shrink = int(rng.integers(5, 10))
                    stock -= shrink
                    validation.append({'issue_type': 'Possible shrinkage or missing outflow', 'branch_id': branch_id, 'product_id': product_id, 'issue_date': date_text})

                recorded = stock
                if key in anomalies['phantom']:
                    recorded = int(rng.integers(6, 22))
                    stock = 0
                    phantom_correction = recorded
                    quantity = int(rng.integers(2, 7))
                    cancellations.append({'cancellation_id': cancellation_id, 'branch_id': branch_id, 'product_id': product_id, 'cancellation_time': current.replace(hour=19).strftime('%Y-%m-%d %H:%M:%S'), 'requested_quantity': quantity, 'reason': 'SYSTEM_SHOWED_AVAILABLE'})
                    cancellation_id += 1
                    validation.append({'issue_type': 'Phantom inventory', 'branch_id': branch_id, 'product_id': product_id, 'issue_date': date_text})

                snapshots.append({'snapshot_id': snapshot_id, 'branch_id': branch_id, 'product_id': product_id, 'snapshot_date': date_text, 'recorded_closing_stock': recorded})
                snapshot_id += 1

    branches.to_csv(RAW_DIR / 'branches.csv', index=False)
    suppliers.to_csv(RAW_DIR / 'suppliers.csv', index=False)
    products.to_csv(RAW_DIR / 'products.csv', index=False)
    pd.DataFrame(sales).to_csv(RAW_DIR / 'sales.csv', index=False)
    pd.DataFrame(orders).to_csv(RAW_DIR / 'supplier_orders.csv', index=False)
    pd.DataFrame(movements).to_csv(RAW_DIR / 'movements.csv', index=False)
    pd.DataFrame(snapshots).to_csv(RAW_DIR / 'snapshots.csv', index=False)
    pd.DataFrame(cancellations).to_csv(RAW_DIR / 'cancellations.csv', index=False)
    pd.DataFrame(validation).to_csv(VALIDATION_DIR / 'known_issues.csv', index=False)

    print(f'Generated {len(branches):,} branches')
    print(f'Generated {len(products):,} products')
    print(f'Generated {len(sales):,} sales rows')
    print(f'Generated {len(movements):,} movements')
    print(f'Generated {len(snapshots):,} snapshots')
    print(f'Generated {len(orders):,} supplier orders')
    print(f'Generated {len(cancellations):,} cancellations')
    print(f'Inserted {len(validation):,} known issues')


if __name__ == '__main__':
    generate_all()
