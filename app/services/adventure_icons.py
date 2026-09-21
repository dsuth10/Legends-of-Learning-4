"""Curated Material Icon catalog and type defaults for adventure nodes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.adventure import NodeType

ICON_CATALOG: List[Dict[str, Any]] = [
    {"id": "flag", "label": "Flag", "ligature": "flag", "default_for": ["start"]},
    {"id": "auto_stories", "label": "Story", "ligature": "auto_stories", "default_for": ["story"]},
    {"id": "swords", "label": "Swords", "ligature": "swords", "default_for": ["battle"]},
    {"id": "quiz", "label": "Quiz", "ligature": "quiz", "default_for": ["quiz"]},
    {"id": "alt_route", "label": "Branch", "ligature": "alt_route", "default_for": ["choice"]},
    {"id": "redeem", "label": "Reward", "ligature": "redeem", "default_for": ["reward"]},
    {"id": "emoji_events", "label": "Milestone", "ligature": "emoji_events", "default_for": ["milestone"]},
    {"id": "cruelty_free", "label": "Boss", "ligature": "cruelty_free", "default_for": ["boss"]},
    {"id": "sports_score", "label": "Finish", "ligature": "sports_score", "default_for": ["end"]},
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
        _DEFAULT_BY_TYPE[_node_type] = _icon["ligature"]

_KNOWN_LIGATURES = {icon["ligature"] for icon in ICON_CATALOG}


def catalog_payload() -> Dict[str, Any]:
    return {"icons": [dict(item) for item in ICON_CATALOG]}


def default_icon_for(node_type: str) -> str:
    if not node_type:
        return "flag"
    return _DEFAULT_BY_TYPE.get(node_type, "flag")


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
