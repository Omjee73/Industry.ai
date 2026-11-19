"""Response models for the PCB inspector API."""

from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class BBoxOut(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ImageInfoOut(BaseModel):
    id: int
    kind: str
    width: int
    height: int
    url: str
    created_at: str


class ImageUploadOut(BaseModel):
    id: int
    width: int
    height: int
    url: str


class AnnotationOut(BaseModel):
    id: int
    name: str
    x: float
    y: float
    width: float
    height: float


class ComponentResultOut(BaseModel):
    name: str
    status: Literal["present", "missing", "review"]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    bbox: BBoxOut


class TestImageInfoOut(BaseModel):
    id: int
    url: str
    width: int
    height: int


class TestImageResultsOut(BaseModel):
    test_image_id: int
    status: Literal["ok", "missing", "review"]
    results: List[ComponentResultOut]
    image: TestImageInfoOut


class InspectionOut(BaseModel):
    id: int
    status: Literal["ok", "missing", "review"]
    reference_image_id: int
    test_images: List[TestImageResultsOut]


class SettingsOut(BaseModel):
    thresholds: Dict[str, float]
    defaults: Dict[str, float]


class DatasetLoadOut(BaseModel):
    reference_id: int
    reference_url: str
    annotations: List[AnnotationOut]
    test_ids: List[int]
    message: str
