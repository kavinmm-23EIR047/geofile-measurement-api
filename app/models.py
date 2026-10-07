import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _uuid() -> str:
    return uuid.uuid4().hex


class GeoFile(Base):
    __tablename__ = "geo_files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=FileStatus.PROCESSING.value)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    crs: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    features: Mapped[list["Feature"]] = relationship(
        back_populates="file", cascade="all, delete-orphan", order_by="Feature.index"
    )


class Feature(Base):
    __tablename__ = "features"

    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("geo_files.id"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    geometry_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # GeoJSON, original CRS
    crs: Mapped[str | None] = mapped_column(String(64), nullable=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)

    # measurements (SI units)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_crs: Mapped[str | None] = mapped_column(String(32), nullable=True)
    measurement_status: Mapped[str] = mapped_column(String(20), default="OK")  # OK | NOT_APPLICABLE | UNSUPPORTED | ERROR
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    file: Mapped[GeoFile] = relationship(back_populates="features")
