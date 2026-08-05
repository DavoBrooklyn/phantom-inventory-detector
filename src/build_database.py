import sqlite3
import pandas as pd
from src.config import DATABASE_PATH, RAW_DIR, SQL_DIR

FILES = [
    ('branches', 'branches.csv'),
    ('suppliers', 'suppliers.csv'),
    ('products', 'products.csv'),
    ('sales', 'sales.csv'),
    ('supplier_orders', 'supplier_orders.csv'),
    ('movements', 'movements.csv'),
    ('snapshots', 'snapshots.csv'),
    ('cancellations', 'cancellations.csv')
]


def build_database():
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute('PRAGMA foreign_keys = ON')
    connection.executescript((SQL_DIR / '01_schema.sql').read_text(encoding='utf-8'))
    for table, file_name in FILES:
        frame = pd.read_csv(RAW_DIR / file_name)
        frame.to_sql(table, connection, if_exists='append', index=False)
        print(f'Loaded {len(frame):,} rows into {table}')
    connection.executescript((SQL_DIR / '02_indexes.sql').read_text(encoding='utf-8'))
    connection.executescript((SQL_DIR / '03_analysis_views.sql').read_text(encoding='utf-8'))
    errors = connection.execute('PRAGMA foreign_key_check').fetchall()
    if errors:
        raise RuntimeError(errors[:10])
    connection.commit()
    connection.close()
    print(f'Database created at {DATABASE_PATH}')


if __name__ == '__main__':
    build_database()
