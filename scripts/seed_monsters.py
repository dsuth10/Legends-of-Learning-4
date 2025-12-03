"""
Seed monsters for the Battle of Wits feature.
"""
from app import create_app
from app.models import db
from app.models.battle import Monster

app = create_app()

with app.app_context():
    # Check if monsters already exist
    if Monster.query.count() > 0:
        print("Monsters already exist. Skipping seed.")
    else:
        monsters = [
            Monster(
                name="Goblin",
                image_url="/static/monsters/goblin.png",
                level=1,
                health=50,
                attack=5,
                defense=3,
                xp_reward=25,
                gold_reward=10
            ),
            Monster(
                name="Orc Warrior",
                image_url="/static/monsters/orc.png",
                level=3,
                health=100,
                attack=10,
                defense=5,
                xp_reward=50,
                gold_reward=25
            ),
            Monster(
                name="Dark Wizard",
                image_url="/static/monsters/wizard.png",
                level=5,
                health=80,
                attack=15,
                defense=4,
                xp_reward=75,
                gold_reward=40
            ),
            Monster(
                name="Dragon",
                image_url="/static/monsters/dragon.png",
                level=10,
                health=200,
                attack=25,
                defense=15,
                xp_reward=200,
                gold_reward=100
            ),
        ]
        
        for monster in monsters:
            db.session.add(monster)
        
        db.session.commit()
        print(f"✓ Seeded {len(monsters)} monsters successfully!")
        
        for monster in monsters:
            print(f"  - {monster.name} (Level {monster.level})")
