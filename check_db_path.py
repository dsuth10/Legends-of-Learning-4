from app.models.db_config import DB_PATH, BASE_DIR
import os

print(f"BASE_DIR: {BASE_DIR}")
print(f"DB_PATH: {DB_PATH}")
print(f"DB_PATH exists: {os.path.exists(DB_PATH)}")
print(f"Instance dir exists: {os.path.exists(os.path.dirname(DB_PATH))}")
