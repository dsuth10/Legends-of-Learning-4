import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import app...")
    from app import create_app
    print("App imported.")
    
    print("Attempting to import db...")
    from app.models import db
    print("DB imported.")

    print("Attempting to import ShopItemOverride...")
    from app.models.shop_config import ShopItemOverride
    print("ShopItemOverride imported.")
    
    print("Checking metadata tables...")
    print(db.metadata.tables.keys())
    
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
