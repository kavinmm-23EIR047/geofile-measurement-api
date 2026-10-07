from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'geo.db'}"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_UNZIPPED_BYTES = 200 * 1024 * 1024  # zip-bomb guard
ALLOWED_EXTENSIONS = {".zip", ".kml"}
