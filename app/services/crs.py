"""CRS helpers: choose a metric projected CRS for a geometry."""
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def utm_epsg_for(lon: float, lat: float) -> int:
    """UTM zone EPSG code (326xx north / 327xx south) for a lon/lat point."""
    zone = int((lon + 180) // 6) + 1
    zone = max(1, min(zone, 60))
    return (32600 if lat >= 0 else 32700) + zone


def to_wgs84(geom: BaseGeometry, source_crs: CRS) -> BaseGeometry:
    if source_crs.equals(CRS.from_epsg(4326)):
        return geom
    t = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
    return transform(t.transform, geom)


def project_to_utm(geom_wgs84: BaseGeometry) -> tuple[BaseGeometry, int]:
    """Reproject a WGS84 geometry into the UTM zone of its centroid."""
    c = geom_wgs84.centroid
    epsg = utm_epsg_for(c.x, c.y)
    t = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(epsg), always_xy=True)
    return transform(t.transform, geom_wgs84), epsg
