"""Request bodies for the PCB inspector API."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field, model_validator


class AnnotationIn(BaseModel):
    """A named component region on the reference board (normalized coordinates)."""

    name: str = Field(min_length=1, max_length=128)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _fits_on_board(self) -> "AnnotationIn":
        if self.x + self.width > 1.0 + 1e-6 or self.y + self.height > 1.0 + 1e-6:
            raise ValueError("annotation must fit within the image bounds")
        return self


class AnnotationsSaveIn(BaseModel):
    annotations: List[AnnotationIn]


class InspectionIn(BaseModel):
    reference_image_id: int
    test_image_ids: List[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _limits(self) -> "InspectionIn":
        if len(self.test_image_ids) > 3:
            raise ValueError("a maximum of 3 test images per inspection is allowed")
        return self


class SettingsUpdateIn(BaseModel):
    thresholds: Dict[str, float] = Field(default_factory=dict)
