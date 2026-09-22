"""Request-derived student chrome: identity, stats, clan strip, party, power icons."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import has_request_context, request

from app.models.character import Character
from app.models.student import Student

PARTY_MEMBER_LIMIT = 3

_POWER_ICONS = {
    "attack": "swords",
    "defense": "shield",
    "heal": "favorite",
    "buff": "upgrade",
    "debuff": "trending_down",
    "utility": "auto_fix",
}

_SPECIAL_EFFECT_ICONS = {
    "revive": "emergency",
    "cheat_death": "health_and_safety",
}


def power_icon_for_ability(ability: Any) -> str:
    """Map Ability.type / special_effect to a Material Icon ligature."""
    if ability is None:
        return "bolt"
    if isinstance(ability, dict):
        effect = ability.get("special_effect")
        ability_type = ability.get("type")
    else:
        effect = getattr(ability, "special_effect", None)
        ability_type = getattr(ability, "type", None)
    if hasattr(ability_type, "value"):
        ability_type = ability_type.value
    effect_key = str(effect or "").strip().lower()
    if effect_key in _SPECIAL_EFFECT_ICONS:
        return _SPECIAL_EFFECT_ICONS[effect_key]
    return _POWER_ICONS.get(str(ability_type or "").strip().lower(), "bolt")


def _bar_percent(current: Optional[int], maximum: Optional[int]) -> int:
    if not maximum or maximum <= 0:
        return 0
    pct = int(round((float(current or 0) / float(maximum)) * 100))
    if pct < 0:
        return 0
    if pct > 100:
        return 100
    return pct


def _equipped_health_bonus(character: Character) -> int:
    bonus = 0
    for item in character.inventory_items.filter_by(is_equipped=True):
        equipment = getattr(item, "equipment", None)
        if equipment is not None:
            bonus += int(getattr(equipment, "health_bonus", 0) or 0)
    return bonus


def _member_stats(character: Character, is_current: bool = False) -> Dict[str, Any]:
    hp_current = int(character.health or 0)
    hp_max = int(character.max_health or 0) + _equipped_health_bonus(character)
    power_current = int(character.power or 0)
    power_max = int(character.max_power or 0)
    return {
        "character": character,
        "id": character.id,
        "name": character.name,
        "avatar_url": character.avatar_url,
        "portrait_url": character.portrait_url,
        "is_current": is_current,
        "hp_current": hp_current,
        "hp_max": hp_max,
        "power_current": power_current,
        "power_max": power_max,
        "hp_percent": _bar_percent(hp_current, hp_max),
        "power_percent": _bar_percent(power_current, power_max),
    }


def _ordered_clan_members(character: Character) -> List[Character]:
    clan = character.clan
    if clan is None:
        return [character]
    others = [
        member
        for member in clan.members.filter_by(is_active=True).all()
        if member.id != character.id
    ]
    return [character] + others


def _classroom_display_name(classroom: Any) -> Optional[str]:
    if classroom is None:
        return None
    return getattr(classroom, "name", None) or getattr(classroom, "class_name", None)


def student_chrome_context(user) -> Dict[str, Any]:
    """Build the shared student-frame context for one request."""
    student_profile = Student.query.filter_by(user_id=user.id).first() if user else None
    classroom = student_profile.classroom if student_profile else None
    if classroom is not None:
        _ = classroom.teacher
    main_character = None
    if student_profile is not None:
        main_character = student_profile.characters.filter_by(is_active=True).first()

    clan = main_character.clan if main_character is not None else None
    class_name = _classroom_display_name(classroom)
    clan_name = clan.name if clan is not None else None

    clan_members: List[Dict[str, Any]] = []
    party_members: List[Dict[str, Any]] = []
    hp_current = hp_max = hp_percent = None
    power_current = power_max = power_percent = None
    xp_current = xp_next = xp_percent = None
    gold = power_points = None

    if main_character is not None:
        ordered = _ordered_clan_members(main_character)
        clan_members = [
            _member_stats(member, is_current=(member.id == main_character.id))
            for member in ordered
        ]
        self_stats = clan_members[0]
        hp_current = self_stats["hp_current"]
        hp_max = self_stats["hp_max"]
        hp_percent = self_stats["hp_percent"]
        power_current = self_stats["power_current"]
        power_max = self_stats["power_max"]
        power_percent = self_stats["power_percent"]
        xp_current = int(main_character.experience or 0)
        xp_next = int(main_character.level or 1) * 1000
        xp_percent = _bar_percent(xp_current, xp_next)
        gold = int(main_character.gold or 0)
        power_points = int(main_character.power_points or 0)
        party_members = [
            {
                "id": member["id"],
                "name": member["name"],
                "avatar_url": member["avatar_url"],
                "portrait_url": member["portrait_url"],
            }
            for member in clan_members[1 : 1 + PARTY_MEMBER_LIMIT]
        ]

    endpoint = request.endpoint if has_request_context() else None
    return {
        "student": user,
        "student_profile": student_profile,
        "main_character": main_character,
        "classroom": classroom,
        "clan": clan,
        "class_name": class_name,
        "clan_name": clan_name,
        "clan_members": clan_members,
        "party_members": party_members,
        "hp_current": hp_current,
        "hp_max": hp_max,
        "hp_percent": hp_percent,
        "power_current": power_current,
        "power_max": power_max,
        "power_percent": power_percent,
        "xp_current": xp_current,
        "xp_next": xp_next,
        "xp_percent": xp_percent,
        "gold": gold,
        "power_points": power_points,
        "current_endpoint": endpoint,
        "power_icon_for_ability": power_icon_for_ability,
    }
