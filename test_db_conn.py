from app.models.db_config import get_database_url
from sqlalchemy import create_engine, text

url = get_database_url()
print(f"Database URL: {url}")

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Connection successful: {result.fetchone()}")
except Exception as e:
    print(f"Connection failed: {e}")
