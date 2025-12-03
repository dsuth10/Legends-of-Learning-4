"""
Drop partially created Battle of Wits tables to allow clean migration.
"""
from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    # Drop tables that may have been partially created
    tables_to_drop = ['battles', 'questions', 'question_sets', 'teachers', 'monsters']
    
    for table in tables_to_drop:
        try:
            db.session.execute(db.text(f'DROP TABLE IF EXISTS {table}'))
            print(f'Dropped table: {table}')
        except Exception as e:
            print(f'Error dropping {table}: {e}')
    
    db.session.commit()
    print('\nAll partial tables dropped successfully.')
