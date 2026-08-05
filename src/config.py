from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
VALIDATION_DIR = ROOT / "data" / "validation"
DATABASE_DIR = ROOT / "database"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_CHART_DIR = OUTPUT_DIR / "charts"
DOCS_CHART_DIR = ROOT / "docs" / "charts"
DOCS_RESULT_DIR = ROOT / "docs" / "results"
SQL_DIR = ROOT / "sql"
DATABASE_PATH = DATABASE_DIR / "phantom_inventory.db"
SEED = 42

for path in [RAW_DIR, VALIDATION_DIR, DATABASE_DIR, OUTPUT_DIR, OUTPUT_CHART_DIR, DOCS_CHART_DIR, DOCS_RESULT_DIR]:
    path.mkdir(parents=True, exist_ok=True)
