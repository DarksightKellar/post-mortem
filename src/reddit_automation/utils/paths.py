from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
OUTPUT_DIR = PROJECT_ROOT / "output"
DB_PATH = DATA_DIR / "app.db"
SCHEMA_SQL_PATH = DATA_DIR / "schema.sql"
