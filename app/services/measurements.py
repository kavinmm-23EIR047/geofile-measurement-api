"""Measurement calculation for a single geometry."""
from dataclasses import dataclass

from pyproj import CRS
from shapely.geometry.base import BaseGeometry

from app.services.crs import project_to_utm, to_wgs84

POLYGONAL = {"Polygon", "MultiPolygon"}
LINEAR = {"LineString", "MultiLineString", "LinearRing"}
POINTS = {"Point", "MultiPoint"}


@dataclass
class Measurement:
    status: str  # OK | NOT_APPLICABLE | UNSUPPORTED | ERROR
    area_m2: float | None = None
    length_m: float | None = None
    measurement_crs: str | None = None
    note: str | None = None


def measure(geom: BaseGeometry | None, source_crs: CRS) -> Measurement:
    """Never raises: any problem is reported through Measurement.status/note."""
    try:
        if geom is None or geom.is_empty:
            return Measurement("UNSUPPORTED", note="Empty or missing geometry")

        gtype = geom.geom_type
        if gtype in POINTS:
            return Measurement("NOT_APPLICABLE", note="No measurement defined for points")
        if gtype not in POLYGONAL | LINEAR:
            return Measurement("UNSUPPORTED", note=f"Measurement not supported for {gtype}")

        # source CRS -> WGS84 -> UTM zone of the feature centroid (metres)
        projected, epsg = project_to_utm(to_wgs84(geom, source_crs))
        crs_label = f"EPSG:{epsg}"

        if gtype in POLYGONAL:
            note = None if geom.is_valid else "Geometry is invalid; area may be unreliable"
            return Measurement("OK", area_m2=projected.area, measurement_crs=crs_label, note=note)
        return Measurement("OK", length_m=projected.length, measurement_crs=crs_label)
    except Exception as exc:  # noqa: BLE001 - one bad feature must not kill the file
        return Measurement("ERROR", note=f"Measurement failed: {exc}")
