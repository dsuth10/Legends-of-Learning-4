"""Atomic node reward distribution and consequence application for Adventures."""



from __future__ import annotations



import logging

from typing import List, Optional



from app.models import db

from app.models.achievement_badge import character_badges

from app.models.adventure import AdventureNode, AdventureRewardType, NodeConsequence, NodeReward

from app.models.audit import AuditLog, EventType

from app.models.equipment import Inventory



logger = logging.getLogger(__name__)





def _character_user_id(character) -> Optional[int]:

    if character.student and character.student.user_id:

        return character.student.user_id

    return None





def _reward_condition_met(reward: NodeReward, score: Optional[int]) -> bool:

    if not reward.is_conditional:

        return True

    condition = reward.condition_json or {}

    min_score = condition.get("min_score_percent")

    if min_score is not None:

        if score is None or score < min_score:

            return False

    return True





def distribute_node_rewards(

    character,

    node: AdventureNode,

    *,

    score: Optional[int] = None,

    session=None,

    commit: bool = False,

) -> List[dict]:

    """Apply all eligible node rewards in the caller's session without committing."""

    if session is None:

        session = db.session



    distributed: List[dict] = []

    rewards = list(node.rewards)



    for reward in rewards:

        if not _reward_condition_met(reward, score):

            continue

        _apply_single_reward(character, reward, node, session)

        distributed.append(

            {

                "type": reward.type,

                "amount": reward.amount,

                "item_id": reward.item_id,

                "ability_id": reward.ability_id,

                "badge_id": reward.badge_id,

            }

        )



    if commit:

        session.commit()

    return distributed





def _apply_single_reward(character, reward: NodeReward, node: AdventureNode, session) -> None:

    session.add(character)

    user_id = _character_user_id(character)

    rtype = reward.type



    if rtype == AdventureRewardType.EXPERIENCE.value:

        old_level = character.level

        old_xp = character.experience

        character.experience += reward.amount

        session.add(

            AuditLog(

                event_type=EventType.XP_GAIN.value,

                event_data={

                    "amount": reward.amount,

                    "old_experience": old_xp,

                    "new_experience": character.experience,

                    "source": "adventure_reward",

                    "node_id": node.id,

                    "adventure_id": node.adventure_id,

                },

                user_id=user_id,

                character_id=character.id,

            )

        )

        new_level = (character.experience // 1000) + 1

        if new_level > character.level:

            levels_gained = new_level - character.level

            character.level = new_level

            character.max_health += 10 * levels_gained

            character.health = character.max_health

            character.max_power += 2 * levels_gained

            character.power = min(character.max_power, character.power + 2 * levels_gained)

            character.defense += 2 * levels_gained

            character.power_points += levels_gained

            session.add(

                AuditLog(

                    event_type=EventType.LEVEL_UP.value,

                    event_data={

                        "old_level": old_level,

                        "new_level": character.level,

                        "levels_gained": levels_gained,

                        "source": "adventure_reward",

                        "node_id": node.id,

                    },

                    user_id=user_id,

                    character_id=character.id,

                )

            )



    elif rtype == AdventureRewardType.GOLD.value:

        old_gold = character.gold

        character.gold += reward.amount

        session.add(

            AuditLog(

                event_type=EventType.GOLD_TRANSACTION.value,

                event_data={

                    "amount": reward.amount,

                    "old_gold": old_gold,

                    "new_gold": character.gold,

                    "source": "adventure_reward",

                    "node_id": node.id,

                },

                user_id=user_id,

                character_id=character.id,

            )

        )



    elif rtype == AdventureRewardType.EQUIPMENT.value and reward.item_id:

        session.add(Inventory(character_id=character.id, item_id=reward.item_id))



    elif rtype == AdventureRewardType.ABILITY.value and reward.ability_id:

        from app.models.ability import CharacterAbility



        session.add(

            CharacterAbility(character_id=character.id, ability_id=reward.ability_id)

        )



    elif rtype == AdventureRewardType.CLAN_EXPERIENCE.value and character.clan:

        clan = character.clan

        session.add(clan)

        clan.experience += reward.amount

        new_clan_level = (clan.experience // 5000) + 1

        if new_clan_level > clan.level:

            clan.level = new_clan_level



    elif rtype == AdventureRewardType.SPECIAL_CURRENCY.value:

        if character.student:

            session.add(character.student)

            character.student.gold += reward.amount



    elif rtype == AdventureRewardType.BADGE.value and reward.badge_id:

        session.execute(

            character_badges.insert().values(

                character_id=character.id,

                badge_id=reward.badge_id,

            )

        )





def apply_node_consequences(

    character,

    node: AdventureNode,

    *,

    session=None,

    commit: bool = False,

) -> dict:

    """Apply all consequences for a node once; does not commit unless requested."""

    if session is None:

        session = db.session



    consequence = node.consequences.first()

    if consequence is None:

        return {}



    session.add(character)

    if consequence.xp_penalty:

        character.experience = max(0, character.experience - consequence.xp_penalty)

    if consequence.gold_penalty:

        character.gold = max(0, character.gold - consequence.gold_penalty)

    if consequence.hp_penalty:

        character.health = max(0, character.health - consequence.hp_penalty)



    result = {

        "xp_penalty": consequence.xp_penalty,

        "gold_penalty": consequence.gold_penalty,

        "hp_penalty": consequence.hp_penalty,

        "description": consequence.description,

    }

    if commit:

        session.commit()

    return result





def apply_node_consequence_row(

    character,

    consequence: NodeConsequence,

    *,

    session=None,

    commit: bool = False,

) -> dict:

    """Apply a specific consequence row (test helper)."""

    if session is None:

        session = db.session

    session.add(character)

    if consequence.xp_penalty:

        character.experience = max(0, character.experience - consequence.xp_penalty)

    if consequence.gold_penalty:

        character.gold = max(0, character.gold - consequence.gold_penalty)

    if consequence.hp_penalty:

        character.health = max(0, character.health - consequence.hp_penalty)

    if commit:

        session.commit()

    return {

        "xp_penalty": consequence.xp_penalty,

        "gold_penalty": consequence.gold_penalty,

        "hp_penalty": consequence.hp_penalty,

    }


