"""Add stable keys to built-in equipment catalogue rows."""
from alembic import op
import sqlalchemy as sa

revision = "20260923_equipment_catalogue_keys"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def _normalise(value):
    return "".join(character.lower() for character in (value or "") if character.isalnum())


def upgrade():
    op.add_column("equipment", sa.Column("catalogue_key", sa.String(length=128), nullable=True))
    op.create_index("uq_equipment_catalogue_key", "equipment", ["catalogue_key"], unique=True)

    # Backfill only rows whose class, slot, type, level, display name and known
    # catalogue image filename agree. Custom equipment without this fingerprint
    # remains unkeyed for the runtime sync command to leave alone.
    from app.models.equipment_data import EQUIPMENT_DATA
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT id, name, type, slot, level_requirement, image_url, class_restriction "
        "FROM equipment WHERE catalogue_key IS NULL"
    )).mappings().all()
    for item in EQUIPMENT_DATA:
        typ = getattr(item["type"], "value", item["type"])
        slot = getattr(item["slot"], "value", item["slot"])
        legacy_names = {item["name"]}
        if item["catalogue_key"] == "sorcerer_1_armor_cloak2":
            legacy_names.add("Sorcerer Cloak II")
        if item["catalogue_key"] == "druid_1_armor_cloak2":
            legacy_names.add("Druid Cloak II")
        wanted_names = {_normalise(name) for name in legacy_names}
        image_stem = _normalise(item["image_url"].rsplit("/", 1)[-1].rsplit(".", 1)[0])
        matches = []
        for row in rows:
            if (row["type"] != typ or row["slot"] != slot or
                    row["class_restriction"] != item.get("class_restriction") or
                    row["level_requirement"] != item["level_requirement"] or
                    row["name"] not in legacy_names):
                continue
            image = row["image_url"] or ""
            if not image.startswith("/static/images/equipment/"):
                continue
            old_stem = _normalise(image.rsplit("/", 1)[-1].rsplit(".", 1)[0])
            if old_stem == image_stem or old_stem in wanted_names:
                matches.append(row["id"])
        if len(matches) == 1:
            connection.execute(sa.text(
                "UPDATE equipment SET catalogue_key = :key, name = :name, image_url = :image_url "
                "WHERE id = :id AND catalogue_key IS NULL"
            ), {
                "key": item["catalogue_key"],
                "name": item["name"],
                "image_url": item["image_url"],
                "id": matches[0],
            })


def downgrade():
    op.drop_index("uq_equipment_catalogue_key", table_name="equipment")
    op.drop_column("equipment", "catalogue_key")
