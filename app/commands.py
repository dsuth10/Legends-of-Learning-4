import click
from flask.cli import with_appcontext
from app.models import db
from app.models.equipment import Equipment
from app.models.equipment_data import EQUIPMENT_DATA
from app.models.ability import Ability
from app.models.ability_data import seed_default_abilities
from sqlalchemy import inspect as sa_inspect

@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Populate the database with initial data."""
    try:
        inspector = sa_inspect(db.engine)
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
                        power_bonus=item['power_bonus'],
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

        if 'abilities' in inspector.get_table_names():
            seed_default_abilities(db, Ability)
            print("Abilities checked / seeded.")
        else:
            print("Abilities table does not exist. Run migrations first.")
    except Exception as e:
        print(f"Error seeding database: {e}")


@click.command('sync-powers')
@with_appcontext
def sync_powers_command():
    """Sync default powers (abilities) — inserts any abilities in ABILITY_DATA that are missing from the DB.

    Run this after adding new abilities to ability_data.py (e.g. Cheat Death) on an
    existing database where seed-db would skip because the table is already populated.

    Usage:
        flask sync-powers
    """
    try:
        inspector = sa_inspect(db.engine)
        if 'abilities' not in inspector.get_table_names():
            print("Abilities table does not exist. Run migrations first.")
            return
        before = Ability.query.count()
        seed_default_abilities(db, Ability)
        after = Ability.query.count()
        added = after - before
        if added:
            print(f"sync-powers: inserted {added} new ability/abilities.")
        else:
            print("sync-powers: all default abilities already present, nothing to insert.")
    except Exception as e:
        print(f"Error syncing powers: {e}")


@click.command('sync-equipment')
@with_appcontext
def sync_equipment_command():
    """Sync equipment from EQUIPMENT_DATA — inserts any equipment items that are missing from the DB.

    Run this after adding new equipment to equipment_data.py on an existing database
    where seed-db would skip because the table is already populated.

    Usage:
        flask sync-equipment
    """
    try:
        inspector = sa_inspect(db.engine)
        if 'equipment' not in inspector.get_table_names():
            print("Equipment table does not exist. Run migrations first.")
            return
        
        before = Equipment.query.count()
        existing_names = {eq.name for eq in Equipment.query.all()}
        added = 0
        
        for item in EQUIPMENT_DATA:
            if item['name'] not in existing_names:
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
                    power_bonus=item['power_bonus'],
                    defense_bonus=item['defense_bonus'],
                    rarity=item['rarity'],
                    image_url=item['image_url'],
                    class_restriction=item.get('class_restriction'),
                )
                db.session.add(eq)
                added += 1
        
        if added:
            db.session.commit()
            print(f"sync-equipment: inserted {added} new equipment item(s).")
        else:
            print("sync-equipment: all equipment items already present, nothing to insert.")
    except Exception as e:
        db.session.rollback()
        print(f"Error syncing equipment: {e}")
