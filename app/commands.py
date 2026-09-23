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
            equipment_columns = {column['name'] for column in inspector.get_columns('equipment')}
            equipment_count = db.session.query(db.func.count(Equipment.id)).scalar()
            if equipment_count == 0 and 'catalogue_key' not in equipment_columns:
                print("Equipment catalogue migration is required before seeding. Run database migrations first.")
            elif equipment_count == 0:
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
                        **({'catalogue_key': item['catalogue_key']} if 'catalogue_key' in equipment_columns else {}),
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
@click.option('--dry-run', is_flag=True, help='Report planned catalogue changes without writing them.')
@with_appcontext
def sync_equipment_command(dry_run=False):
    """Synchronise known catalogue rows by stable key or legacy image identity.

    Existing equipment rows are updated in place, preserving IDs and all foreign-key
    references. Rows without a recognised catalogue key or image identity are kept.
    """
    try:
        inspector = sa_inspect(db.engine)
        if 'equipment' not in inspector.get_table_names():
            raise click.ClickException("Equipment table does not exist. Run migrations first.")
        if 'catalogue_key' not in {column['name'] for column in inspector.get_columns('equipment')}:
            raise click.ClickException(
                "Equipment catalogue-key migration is required. Run database migrations first."
            )

        def enum_value(value):
            return value.value if hasattr(value, 'value') else value

        def normalise(value):
            return ''.join(character.lower() for character in (value or '') if character.isalnum())

        rows = Equipment.query.order_by(Equipment.id).all()
        keyed = {row.catalogue_key: row for row in rows if row.catalogue_key}
        claimed_ids = set()
        planned_adds, planned_updates, unchanged = [], [], []

        for item in EQUIPMENT_DATA:
            key = item['catalogue_key']
            row = keyed.get(key)
            if row is None:
                expected_type = enum_value(item['type'])
                expected_slot = enum_value(item['slot'])
                legacy_names = {item['name']}
                if key == 'sorcerer_1_armor_cloak2':
                    legacy_names.add('Sorcerer Cloak II')
                elif key == 'druid_1_armor_cloak2':
                    legacy_names.add('Druid Cloak II')
                name_tokens = {normalise(name) for name in legacy_names}
                canonical_token = normalise(item['image_url'].rsplit('/', 1)[-1].rsplit('.', 1)[0])
                candidates = []
                for existing in rows:
                    if existing.id in claimed_ids or existing.catalogue_key:
                        continue
                    if (existing.type != expected_type or existing.slot != expected_slot or
                            existing.class_restriction != item.get('class_restriction') or
                            existing.level_requirement != item['level_requirement']):
                        continue
                    image = existing.image_url or ''
                    if not image.startswith('/static/images/equipment/'):
                        continue
                    # Asset paths can be reused by teacher-created gear. Require
                    # a recognised legacy catalogue name as well as the image.
                    if normalise(existing.name) not in name_tokens:
                        continue
                    legacy_token = normalise(image.rsplit('/', 1)[-1].rsplit('.', 1)[0])
                    if legacy_token == canonical_token or legacy_token in name_tokens:
                        candidates.append(existing)
                if len(candidates) == 1:
                    row = candidates[0]

            values = {
                'catalogue_key': item['catalogue_key'],
                'name': item['name'],
                'description': item['description'],
                'type': enum_value(item['type']),
                'slot': enum_value(item['slot']),
                'cost': item['cost'],
                'level_requirement': item['level_requirement'],
                'health_bonus': item['health_bonus'],
                'power_bonus': item['power_bonus'],
                'defense_bonus': item['defense_bonus'],
                'rarity': item['rarity'],
                'image_url': item['image_url'],
                'class_restriction': item.get('class_restriction'),
            }
            if row is None:
                planned_adds.append(item['catalogue_key'])
                if not dry_run:
                    row = Equipment(**values)
                    db.session.add(row)
                    db.session.flush()
            else:
                claimed_ids.add(row.id)
                # Stable-key sync owns catalogue identity and presentation. Keep
                # gameplay balance values already present in a live database.
                balance_fields = {
                    'cost', 'health_bonus', 'power_bonus', 'defense_bonus',
                    'level_requirement', 'rarity',
                }
                update_values = {
                    name: value for name, value in values.items()
                    if name not in balance_fields
                }
                changed = [
                    name for name, value in update_values.items()
                    if getattr(row, name) != value
                ]
                if changed:
                    planned_updates.append((key, changed))
                    if not dry_run:
                        for name, value in update_values.items():
                            setattr(row, name, value)
                else:
                    unchanged.append(key)

        if not dry_run:
            db.session.commit()
        click.echo(f"sync-equipment: {len(planned_adds)} insert(s), {len(planned_updates)} update(s), {len(unchanged)} unchanged.")
        for key, changed in planned_updates:
            click.echo(f"  update {key}: {', '.join(changed)}")
        if dry_run:
            click.echo("Dry run: no changes written.")
    except click.ClickException:
        raise
    except Exception as e:
        db.session.rollback()
        raise click.ClickException(f"Error syncing equipment: {e}") from e
