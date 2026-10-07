import pytest
from pyproj import CRS
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon

from app.services.crs import utm_epsg_for
from app.services.measurements import measure

WGS84 = CRS.from_epsg(4326)
SQ = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98)])


def test_utm_zone_selection():
    assert utm_epsg_for(77.59, 12.97) == 32643   # Bengaluru
    assert utm_epsg_for(-74.0, 40.7) == 32618    # New York
    assert utm_epsg_for(151.2, -33.9) == 32756   # Sydney (south)


def test_multipolygon_area_is_sum():
    shifted = Polygon([(x + 1, y) for x, y in SQ.exterior.coords])
    one = measure(SQ, WGS84).area_m2
    both = measure(MultiPolygon([SQ, shifted]), WGS84).area_m2
    assert both == pytest.approx(2 * one, rel=0.01)


def test_geometry_collection_is_unsupported_not_crash():
    m = measure(GeometryCollection([SQ]), WGS84)
    assert m.status == "UNSUPPORTED"


def test_none_geometry():
    assert measure(None, WGS84).status == "UNSUPPORTED"
