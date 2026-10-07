"""Orchestrates: save -> parse -> measure -> persist."""
import shutil
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Feature, FileStatus, GeoFile
from app.services.parser import InvalidGeoFile, parse_file


def process_file(db: Session, record: GeoFile, path: Path) -> GeoFile:
    workdir = Path(tempfile.mkdtemp(prefix="geo_"))
    try:
        parsed = parse_file(path, workdir)
        record.crs = parsed.crs_label
        record.feature_count = len(parsed.features)
        record.features = [
            Feature(
                index=f.index,
                geometry_type=f.geometry_type,
                geometry=f.geometry,
                crs=parsed.crs_label,
                properties=f.properties,
                area_m2=f.measurement.area_m2,
                length_m=f.measurement.length_m,
                measurement_crs=f.measurement.measurement_crs,
                measurement_status=f.measurement.status,
                note=f.measurement.note,
            )
            for f in parsed.features
        ]
        record.status = FileStatus.COMPLETED.value
    except InvalidGeoFile as exc:
        record.status = FileStatus.FAILED.value
        record.error = str(exc)
    except Exception as exc:  # noqa: BLE001
        record.status = FileStatus.FAILED.value
        record.error = f"Unexpected error: {exc}"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    db.add(record)
    db.commit()
    return record
