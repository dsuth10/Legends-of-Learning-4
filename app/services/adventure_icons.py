"""Adventure node artwork catalog and type defaults."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.adventure import NodeType

ICON_CATALOG: List[Dict[str, Any]] = [
    {"id": "start", "label": "Start", "ligature": "flag", "image_url": "/static/images/adventure_node_icons/node_start.png", "default_for": ["start"]},
    {"id": "story", "label": "Story", "ligature": "auto_stories", "image_url": "/static/images/adventure_node_icons/node_story.png", "default_for": ["story"]},
    {"id": "battle", "label": "Battle", "ligature": "swords", "image_url": "/static/images/adventure_node_icons/node_battle.png", "default_for": ["battle"]},
    {"id": "quiz", "label": "Quiz", "ligature": "quiz", "image_url": "/static/images/adventure_node_icons/node_quiz.png", "default_for": ["quiz"]},
    {"id": "choice", "label": "Choice", "ligature": "alt_route", "image_url": "/static/images/adventure_node_icons/node_choice.png", "default_for": ["choice"]},
    {"id": "reward", "label": "Reward", "ligature": "redeem", "image_url": "/static/images/adventure_node_icons/node_treasure.png", "default_for": ["reward"]},
    {"id": "milestone", "label": "Milestone", "ligature": "emoji_events", "image_url": "/static/images/adventure_node_icons/node_milestone.png", "default_for": ["milestone"]},
    {"id": "boss", "label": "Boss", "ligature": "cruelty_free", "image_url": "/static/images/adventure_node_icons/node_boss.png", "default_for": ["boss"]},
    {"id": "end", "label": "Finish", "ligature": "sports_score", "image_url": "/static/images/adventure_node_icons/node_end.png", "default_for": ["end"]},
    {"id": "quest", "label": "Quest", "ligature": "explore", "image_url": "/static/images/adventure_node_icons/node_quest.png", "default_for": []},
    {"id": "rest", "label": "Rest", "ligature": "bedtime", "image_url": "/static/images/adventure_node_icons/node_rest.png", "default_for": []},
    {"id": "castle", "label": "Castle", "ligature": "castle", "default_for": []},
    {"id": "forest", "label": "Forest", "ligature": "forest", "default_for": []},
    {"id": "pets", "label": "Creature", "ligature": "pets", "default_for": []},
    {"id": "local_fire_department", "label": "Fire", "ligature": "local_fire_department", "default_for": []},
    {"id": "psychology", "label": "Mind", "ligature": "psychology", "default_for": []},
    {"id": "shield", "label": "Shield", "ligature": "shield", "default_for": []},
]

_DEFAULT_BY_TYPE = {}
for _icon in ICON_CATALOG:
    for _node_type in _icon["default_for"]:
        _DEFAULT_BY_TYPE[_node_type] = _icon["image_url"]

_KNOWN_LIGATURES = {icon["ligature"] for icon in ICON_CATALOG}


def catalog_payload() -> Dict[str, Any]:
    return {"icons": [dict(item) for item in ICON_CATALOG]}


def default_icon_for(node_type: str) -> str:
    if not node_type:
        return "flag"
    return _DEFAULT_BY_TYPE.get(node_type, "/static/images/adventure_node_icons/node_start.png")


def normalize_icon_url(value: Optional[str]) -> Optional[str]:
    """Treat empty string as a cleared override. Keep catalog ligatures and / paths."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def known_ligature(value: Optional[str]) -> bool:
    return bool(value) and value in _KNOWN_LIGATURES


def all_node_types_have_one_default() -> bool:
    expected = {item.value for item in NodeType}
    defaults = [
        node_type
        for icon in ICON_CATALOG
        for node_type in icon["default_for"]
    ]
    return set(defaults) == expected and len(defaults) == len(expected)
