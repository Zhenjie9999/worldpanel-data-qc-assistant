from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "local_data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "worldpanel_qc.sqlite3"
LLM_SETTINGS_PATH = DATA_DIR / "llm-settings.json"
STATIC_DIR = ROOT / "static"

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".pptx", ".pdf", ".ppt"}

for directory in [DATA_DIR, UPLOAD_DIR, EXPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
