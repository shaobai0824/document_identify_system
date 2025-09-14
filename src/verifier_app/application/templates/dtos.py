"""
範本管理 DTOs
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class BoundingBoxDto(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class FieldDefinitionCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bbox: BoundingBoxDto
    required: bool = False


class FieldDefinitionDto(BaseModel):
    id: str
    name: str
    bbox: BoundingBoxDto
    required: bool
    suggested: bool = False


class TemplateCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class TemplateUpdateDto(BaseModel):
    name: Optional[str] = None
    field_definitions: Optional[List[FieldDefinitionDto]] = None


class TemplateDto(BaseModel):
    id: str
    name: str
    base_image_url: Optional[str]
    field_definitions: List[FieldDefinitionDto]
    version: str
    status: str
    created_at: str
    updated_at: Optional[str]


class TemplateListDto(BaseModel):
    object: str = "list"
    data: List[TemplateDto]
    has_more: bool = False
    total_count: Optional[int] = None
