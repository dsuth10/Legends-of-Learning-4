from pathlib import Path

import pytest

from app.models.character import Character


@pytest.mark.parametrize("level,band", [(1, 1), (10, 1), (11, 2), (20, 2), (21, 3)])
@pytest.mark.parametrize("character_class", ["Warrior", "Sorcerer", "Druid"])
@pytest.mark.parametrize("appearance_gender", ["male", "female"])
@pytest.mark.parametrize("option", [1, 2, 3])
def test_selected_portrait_and_background_follow_level_band(
    level, band, character_class, appearance_gender, option
):
    stored_choice = Character.portrait_selection_url(
        character_class, appearance_gender, option
    )
    character = Character(
        name="Hero",
        student_id=1,
        character_class=character_class,
        gender="Other",
        avatar_url=stored_choice,
        level=level,
    )
    expected = (
        f"/static/images/characters/{character_class.lower()}/{appearance_gender}/"
        f"level{band}/{option}_{character_class.lower()}_{appearance_gender}_level{band}.png"
    )

    assert character.portrait_url == expected
    assert Path("static", expected.removeprefix("/static/")).is_file()
    assert character.background_url == (
        f"/static/images/Backgrounds/Core Level Backgrounds/Level {band}.png"
    )
    assert Path("static", character.background_url.removeprefix("/static/")).is_file()


def test_portrait_fallback_and_legacy_compact_avatar_mapping():
    other_without_choice = Character(
        name="Hero", student_id=1, character_class="Warrior", gender="Other"
    )
    legacy = Character(
        name="Hero",
        student_id=1,
        character_class="Sorcerer",
        gender="Other",
        avatar_url="/static/avatars/sorcerer_f.png",
        level=12,
    )
    legacy_level_choice = Character(
        name="Hero",
        student_id=1,
        character_class="Druid",
        gender="Other",
        avatar_url="/static/images/characters/druid/female/level1/2_druid_female_level1.png",
        level=21,
    )

    assert other_without_choice.portrait_url == "/static/avatars/default.png"
    assert legacy.portrait_url == (
        "/static/images/characters/sorcerer/female/level2/1_sorcerer_female_level2.png"
    )
    assert legacy_level_choice.portrait_url == (
        "/static/images/characters/druid/female/level3/2_druid_female_level3.png"
    )
    assert Character.normalise_portrait_selection(
        "Sorcerer", "Other", "/static/avatars/sorcerer_f.png"
    ) == Character.portrait_selection_url("Sorcerer", "female", 1)
    assert Character.normalise_portrait_selection(
        "Warrior", "Other", None
    ) is None


def test_character_creation_persists_independent_other_appearance(
    client, db_session, test_user, test_student
):
    client.post("/auth/login", data={"username": test_user.username, "password": "password"})
    create_page = client.get("/student/character/create")
    assert create_page.status_code == 200
    assert b"Masculine style" in create_page.data
    assert b"Feminine style" in create_page.data
    assert "Gender “Other” does not select artwork for you." in create_page.get_data(as_text=True)

    response = client.post(
        "/student/character/create",
        data={
            "name": "Fern",
            "character_class": "Druid",
            "gender": "Other",
            "portrait_gender": "female",
            "portrait_option": "3",
            "avatar_url": "/static/images/characters/druid/female/level1/3_druid_female_level1.png",
        },
    )
    assert response.status_code == 302

    character = test_student.characters.filter_by(is_active=True).first()
    assert character.gender == "Other"
    assert character.avatar_url == Character.portrait_selection_url("Druid", "female", 3)
    assert character.portrait_url.endswith("/level1/3_druid_female_level1.png")

    profile = client.get("/student/character")
    equipment = client.get("/student/equipment")
    assert profile.status_code == 200
    assert equipment.status_code == 200
    assert b"/static/images/characters/druid/female/level1/3_druid_female_level1.png" in profile.data
    assert b"/static/images/Backgrounds/Core Level Backgrounds/Level 1.png" in profile.data
    assert b"/static/images/characters/druid/female/level1/3_druid_female_level1.png" in equipment.data
    assert b"/static/images/Backgrounds/Core Level Backgrounds/Level 1.png" in equipment.data
