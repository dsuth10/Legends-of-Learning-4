from pathlib import Path
from types import SimpleNamespace


def test_seeded_monster_portrait_paths_have_local_pngs():
    expected = {
        "goblin": "/static/monsters/goblin.png",
        "orc": "/static/monsters/orc.png",
        "wizard": "/static/monsters/wizard.png",
        "dragon": "/static/monsters/dragon.png",
    }
    seed_source = Path("scripts/seed_monsters.py").read_text(encoding="utf-8")
    for slug, url in expected.items():
        assert f'image_url="{url}"' in seed_source
        assert Path("static", url.removeprefix("/static/")).is_file()


def test_monster_portrait_shows_local_image_and_accessible_fallback(app):
    fight_source = Path("app/templates/student/battle/fight.html").read_text(
        encoding="utf-8"
    )
    player_section, monster_and_rest = fight_source.split(
        'card border-danger', maxsplit=1
    )
    monster_section = monster_and_rest.split(
        '{% if equipped_abilities %}', maxsplit=1
    )[0]
    assert "monster_portrait(battle.monster)" not in player_section
    assert "monster_portrait(battle.monster)" in monster_section

    with app.app_context():
        for page in ("arena.html", "fight.html", "results.html"):
            app.jinja_env.get_template(f"student/battle/{page}")
        template = app.jinja_env.get_template(
            "student/battle/_monster_portrait.html"
        ).module
        local = template.monster_portrait(
            SimpleNamespace(name="Goblin", image_url="/static/monsters/goblin.png"),
            "sm",
        )
        absent = template.monster_portrait(
            SimpleNamespace(name="Custom monster", image_url=None)
        )
        remote = template.monster_portrait(
            SimpleNamespace(name="Custom monster", image_url="https://example.test/monster.png")
        )

    assert 'src="/static/monsters/goblin.png"' in local
    assert "Portrait unavailable for Goblin" not in local
    assert "Portrait unavailable for Custom monster" in absent
    assert "Portrait unavailable for Custom monster" in remote
    assert "https://example.test/monster.png" not in remote
