from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    feature_count: int
    crs: str | None
    status: str
    error: str | None = None
    created_at: datetime


class FeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    index: int
    geometry_type: str | None
    geometry: dict | None
    crs: str | None
    properties: dict


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    index: int
    geometry_type: str | None
    status: str = Field(validation_alias="measurement_status")
    area_m2: float | None
    length_m: float | None
    measurement_crs: str | None
    note: str | None


class MeasurementsResponse(BaseModel):
    file_id: str
    count: int
    measurements: list[MeasurementOut]


class FeaturesResponse(BaseModel):
    file_id: str
    count: int
    features: list[FeatureOut]
