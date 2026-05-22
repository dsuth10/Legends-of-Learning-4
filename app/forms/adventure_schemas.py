"""Pydantic request/response schemas for the Adventures API."""



from datetime import datetime

from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union



from pydantic import BaseModel, Field, field_validator, model_validator



from app.models.adventure import (

    AdventureRewardType,

    AdventureStatus,

    EdgeConditionType,

    EndSemantics,

    NodeType,

    UnlockSemantics,

)



T = TypeVar("T")





# ---------------------------------------------------------------------------

# Shared API envelope (T013)

# ---------------------------------------------------------------------------





class ApiErrorSchema(BaseModel):

    code: str

    message: str

    node_slug: Optional[str] = None

    affected_students: Optional[int] = None





class ApiResponseSchema(BaseModel, Generic[T]):

    success: bool

    data: Optional[T] = None

    errors: List[ApiErrorSchema] = Field(default_factory=list)





class ValidationIssueSchema(BaseModel):

    code: str

    message: str

    node_slug: Optional[str] = None





class PublishValidationSchema(BaseModel):

    ok_to_publish: bool

    errors: List[ValidationIssueSchema] = Field(default_factory=list)

    warnings: List[ValidationIssueSchema] = Field(default_factory=list)





def success_response(data: Any = None) -> dict:

    """Build a JSON-serializable success envelope."""

    return {"success": True, "data": data, "errors": []}





def error_response(

    code: str,

    message: str,

    *,

    extra_errors: Optional[List[dict]] = None,

) -> dict:

    """Build a JSON-serializable error envelope."""

    errors = [{"code": code, "message": message}]

    if extra_errors:

        errors.extend(extra_errors)

    return {"success": False, "data": None, "errors": errors}





# ---------------------------------------------------------------------------

# Edge condition discriminated unions (T014)

# ---------------------------------------------------------------------------





class AlwaysConditionData(BaseModel):

    pass





class ChoiceConditionData(BaseModel):

    choice_key: str = Field(min_length=1)





class CriteriaConditionData(BaseModel):

    min_score_percent: Optional[int] = Field(default=None, ge=1, le=100)

    completed_within_seconds: Optional[int] = Field(default=None, gt=0)

    no_failed_attempts: Optional[bool] = None



    @model_validator(mode="after")

    def at_least_one_criterion(self):

        if (

            self.min_score_percent is None

            and self.completed_within_seconds is None

            and self.no_failed_attempts is None

        ):

            raise ValueError("criteria condition requires at least one criterion")

        return self





class EdgeCreateSchema(BaseModel):

    from_node_id: int

    to_node_id: int

    label: Optional[str] = None

    condition_type: EdgeConditionType = EdgeConditionType.ALWAYS

    condition_data: Dict[str, Any] = Field(default_factory=dict)

    unlock_semantics: UnlockSemantics = UnlockSemantics.AND

    sort_order: int = 0



    @model_validator(mode="after")

    def validate_condition(self):

        if self.from_node_id == self.to_node_id:

            raise ValueError("self-loops are not allowed")

        validate_edge_condition_pair(self.condition_type, self.condition_data)

        return self





def validate_edge_condition_pair(
    condition_type: EdgeConditionType,
    condition_data: Optional[Dict[str, Any]],
) -> None:
    """Validate condition_type + condition_data together (create and update)."""
    data = condition_data or {}
    if condition_type == EdgeConditionType.ALWAYS:
        AlwaysConditionData.model_validate(data)
        if data:
            raise ValueError("always condition_data must be empty")
    elif condition_type == EdgeConditionType.CHOICE:
        ChoiceConditionData.model_validate(data)
    elif condition_type == EdgeConditionType.CRITERIA:
        CriteriaConditionData.model_validate(data)


class EdgeUpdateSchema(BaseModel):

    label: Optional[str] = None

    condition_type: Optional[EdgeConditionType] = None

    condition_data: Optional[Dict[str, Any]] = None

    unlock_semantics: Optional[UnlockSemantics] = None

    sort_order: Optional[int] = None

    @model_validator(mode="after")
    def validate_condition(self):
        if self.condition_type is not None and self.condition_data is not None:
            validate_edge_condition_pair(self.condition_type, self.condition_data)
        elif self.condition_type == EdgeConditionType.ALWAYS and self.condition_data is None:
            pass
        elif self.condition_type in (
            EdgeConditionType.CHOICE,
            EdgeConditionType.CRITERIA,
        ) and self.condition_data is None:
            raise ValueError(
                f"{self.condition_type.value} edges require condition_data on update"
            )
        return self





# ---------------------------------------------------------------------------

# Reward / consequence schemas (T014)

# ---------------------------------------------------------------------------





class NodeRewardCreateSchema(BaseModel):

    type: AdventureRewardType

    amount: int = 0

    item_id: Optional[int] = None

    ability_id: Optional[int] = None

    badge_id: Optional[int] = None

    is_conditional: bool = False

    condition_json: Dict[str, Any] = Field(default_factory=dict)



    @model_validator(mode="after")

    def validate_type_fks(self):

        amount_types = {

            AdventureRewardType.EXPERIENCE,

            AdventureRewardType.GOLD,

            AdventureRewardType.CLAN_EXPERIENCE,

            AdventureRewardType.SPECIAL_CURRENCY,

        }

        if self.type in amount_types:

            if self.amount <= 0:

                raise ValueError(f"{self.type.value} rewards require amount > 0")

            if self.item_id or self.ability_id or self.badge_id:

                raise ValueError(f"{self.type.value} rewards must not set item/ability/badge FKs")

        elif self.type == AdventureRewardType.EQUIPMENT:

            if not self.item_id:

                raise ValueError("equipment rewards require item_id")

        elif self.type == AdventureRewardType.ABILITY:

            if not self.ability_id:

                raise ValueError("ability rewards require ability_id")

        elif self.type == AdventureRewardType.BADGE:

            if not self.badge_id:

                raise ValueError("badge rewards require badge_id")

        return self





class NodeConsequenceCreateSchema(BaseModel):

    description: Optional[str] = None

    xp_penalty: int = 0

    gold_penalty: int = 0

    hp_penalty: int = 0

    custom_json: Dict[str, Any] = Field(default_factory=dict)





# ---------------------------------------------------------------------------

# Teacher adventure / node / assignment schemas (T014)

# ---------------------------------------------------------------------------





class AdventureCreateSchema(BaseModel):

    title: str = Field(min_length=1, max_length=128)

    description: Optional[str] = None

    background_image_url: Optional[str] = None

    theme: str = "fantasy"

    width: int = Field(default=2000, ge=100)

    height: int = Field(default=1500, ge=100)

    end_semantics: EndSemantics = EndSemantics.ALL





class AdventureUpdateSchema(BaseModel):

    title: Optional[str] = Field(default=None, min_length=1, max_length=128)

    description: Optional[str] = None

    background_image_url: Optional[str] = None

    theme: Optional[str] = None

    width: Optional[int] = Field(default=None, ge=100)

    height: Optional[int] = Field(default=None, ge=100)

    is_public: Optional[bool] = None

    end_semantics: Optional[EndSemantics] = None





class AdventureCloneSchema(BaseModel):

    title: Optional[str] = None





class NodeCreateSchema(BaseModel):

    slug: str = Field(min_length=1, max_length=64)

    title: str = Field(min_length=1, max_length=128)

    description: Optional[str] = None

    lore: Optional[str] = None

    icon_url: Optional[str] = None

    node_type: NodeType

    x: float = Field(default=0.0, ge=0)

    y: float = Field(default=0.0, ge=0)

    is_optional: bool = False

    is_start: bool = False

    is_end: bool = False

    question_set_id: Optional[int] = None

    monster_id: Optional[int] = None

    completion_rules: Dict[str, Any] = Field(default_factory=dict)

    on_complete_actions: Dict[str, Any] = Field(default_factory=dict)

    rewards: List[NodeRewardCreateSchema] = Field(default_factory=list)





class NodeUpdateSchema(BaseModel):

    slug: Optional[str] = Field(default=None, min_length=1, max_length=64)

    title: Optional[str] = Field(default=None, min_length=1, max_length=128)

    description: Optional[str] = None

    lore: Optional[str] = None

    icon_url: Optional[str] = None

    node_type: Optional[NodeType] = None

    x: Optional[float] = Field(default=None, ge=0)

    y: Optional[float] = Field(default=None, ge=0)

    is_optional: Optional[bool] = None

    is_start: Optional[bool] = None

    is_end: Optional[bool] = None

    question_set_id: Optional[int] = None

    monster_id: Optional[int] = None

    completion_rules: Optional[Dict[str, Any]] = None

    on_complete_actions: Optional[Dict[str, Any]] = None





class AssignmentCreateSchema(BaseModel):

    classroom_id: Optional[int] = None

    clan_id: Optional[int] = None

    character_id: Optional[int] = None

    starts_at: Optional[datetime] = None

    ends_at: Optional[datetime] = None



    @model_validator(mode="after")

    def exactly_one_target(self):

        targets = [self.classroom_id, self.clan_id, self.character_id]

        if sum(1 for t in targets if t is not None) != 1:

            raise ValueError("exactly one of classroom_id, clan_id, character_id is required")

        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:

            raise ValueError("ends_at must be after starts_at")

        return self





class AssignmentUpdateSchema(BaseModel):

    starts_at: Optional[datetime] = None

    ends_at: Optional[datetime] = None

    is_active: Optional[bool] = None





class BackgroundUploadSchema(BaseModel):

    """Metadata-only; actual upload is multipart form field ``file``."""



    filename: str = Field(min_length=1)





# ---------------------------------------------------------------------------

# Student lifecycle schemas (T015)

# ---------------------------------------------------------------------------





class NodeStartSchema(BaseModel):

    """Empty body allowed; schema exists for future optional flags."""



    preview: bool = False





class NodeCompleteSchema(BaseModel):

    score: Optional[int] = Field(default=None, ge=0, le=100)





class NodeRetrySchema(BaseModel):

    pass





class NodeChooseSchema(BaseModel):

    choice_key: str = Field(min_length=1)





class ForceCompleteSchema(BaseModel):

    reason: Optional[str] = None





class QuizAnswerSchema(BaseModel):

    question_id: int

    answer: str





class QuizSubmitSchema(BaseModel):

    answers: List[QuizAnswerSchema] = Field(min_length=1)





# ---------------------------------------------------------------------------

# Response DTOs (optional serialization helpers)

# ---------------------------------------------------------------------------





class OwnerSummarySchema(BaseModel):

    id: int

    name: str





class AdventureSummarySchema(BaseModel):

    id: int

    title: str

    description: Optional[str] = None

    status: AdventureStatus

    is_public: bool

    version: int

    theme: str = "fantasy"

    width: int = 2000

    height: int = 1500

    end_semantics: EndSemantics = EndSemantics.ALL

    background_image_url: Optional[str] = None

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None



    model_config = {"from_attributes": True}





class NodeRewardResponseSchema(BaseModel):

    id: int

    type: AdventureRewardType

    amount: int

    item_id: Optional[int] = None

    ability_id: Optional[int] = None

    badge_id: Optional[int] = None

    is_conditional: bool

    condition_json: Dict[str, Any] = Field(default_factory=dict)



    model_config = {"from_attributes": True}





class NodeConsequenceResponseSchema(BaseModel):

    id: int

    description: Optional[str] = None

    xp_penalty: int

    gold_penalty: int

    hp_penalty: int

    custom_json: Dict[str, Any] = Field(default_factory=dict)



    model_config = {"from_attributes": True}


