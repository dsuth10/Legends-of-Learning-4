import click
from flask.cli import with_appcontext
from app.models import db
from app.models.equipment import Equipment
from app.models.equipment_data import EQUIPMENT_DATA
from sqlalchemy import inspect

@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Populate the database with initial data."""
    try:
        # Check if table exists first to avoid OperationalError during migration
        inspector = inspect(db.engine)
        if 'equipment' in inspector.get_table_names():
            if Equipment.query.count() == 0:
                print("Seeding equipment data...")
                for item in EQUIPMENT_DATA:
                    type_value = item['type'].value if hasattr(item['type'], 'value') else item['type']
                    slot_value = item['slot'].value if hasattr(item['slot'], 'value') else item['slot']
                    eq = Equipment(
                        name=item['name'],
                        description=item['description'],
                        type=type_value,
                        slot=slot_value,
                        cost=item['cost'],
                        level_requirement=item['level_requirement'],
                        health_bonus=item['health_bonus'],
                        strength_bonus=item['strength_bonus'],
                        defense_bonus=item['defense_bonus'],
                        rarity=item['rarity'],
                        image_url=item['image_url'],
                        class_restriction=item.get('class_restriction'),
                    )
                    db.session.add(eq)
                db.session.commit()
                print("Equipment seeded successfully.")
            else:
                print("Equipment table already populated.")
        else:
            print("Equipment table does not exist. Run migrations first.")
    except Exception as e:
        print(f"Error seeding database: {e}")
