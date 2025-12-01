import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
try:
    import flask
    print(f"Flask version: {flask.__version__}")
    import pytest
    print(f"pytest version: {pytest.__version__}")
    from app import create_app
    print("Successfully imported create_app")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
