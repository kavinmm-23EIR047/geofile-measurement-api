from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ALLOWED_EXTENSIONS
from app.database import get_db
from app.models import Feature, FileStatus, GeoFile
from app.schemas import FeaturesResponse, FileOut, MeasurementsResponse
from app.services.processing import process_file
from app.services.storage import save_upload

router = APIRouter(prefix="/api/files", tags=["files"])


def _get_file_or_404(db: Session, file_id: str) -> GeoFile:
    record = db.get(GeoFile, file_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return record


def _require_completed(record: GeoFile) -> None:
    if record.status != FileStatus.COMPLETED.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"File status is {record.status}" + (f": {record.error}" if record.error else ""),
        )


@router.post("/", response_model=FileOut, status_code=status.HTTP_201_CREATED)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Unsupported file type. Upload a .zip (Shapefile) or .kml"
        )
    record = GeoFile(filename=Path(file.filename).name)
    db.add(record)
    db.commit()
    try:
        path = save_upload(record.id, file, suffix)
    except ValueError:
        db.delete(record)
        db.commit()
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    return process_file(db, record, path)


@router.get("/{file_id}/", response_model=FileOut)
def get_file(file_id: str, db: Session = Depends(get_db)):
    return _get_file_or_404(db, file_id)


@router.get("/{file_id}/features/", response_model=FeaturesResponse)
def get_features(file_id: str, db: Session = Depends(get_db)):
    record = _get_file_or_404(db, file_id)
    _require_completed(record)
    return FeaturesResponse(file_id=record.id, count=len(record.features), features=record.features)


@router.get("/{file_id}/measurements/", response_model=MeasurementsResponse)
def get_measurements(
    file_id: str,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    record = _get_file_or_404(db, file_id)
    _require_completed(record)
    rows = db.scalars(
        select(Feature)
        .where(Feature.file_id == file_id)
        .order_by(Feature.index)
        .offset(skip)
        .limit(min(limit, 5000))
    ).all()
    return MeasurementsResponse(file_id=record.id, count=record.feature_count, measurements=rows)
