from setuptools import setup, find_packages

setup(
    name="legends-of-learning",
    version="3.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=3.0",
        "SQLAlchemy>=2.0",
        "Flask-Login>=0.6.2",
        "Alembic>=1.12",
        "Werkzeug>=3.0",
        "Flask-WTF>=1.2",
        "WTForms>=3.0",
        "pytest>=7.4",
        "python-dotenv>=1.0",
        "Flask-Migrate>=4.0",
        "Flask-CORS>=4.0",
        "pandas>=2.1",
        "numpy>=1.24",
    ],
) 