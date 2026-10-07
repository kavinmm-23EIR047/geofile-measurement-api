"""Read Shapefile (.zip) / KML into a list of plain feature dicts."""
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from pyproj import CRS
from shapely.geometry import mapping

from app.config import MAX_UNZIPPED_BYTES
from app.services.measurements import measure


class InvalidGeoFile(Exception):
    """Raised for user-fixable problems (bad zip, no .shp, missing CRS...)."""


@dataclass
class ParsedFeature:
    index: int
    geometry_type: str | None
    geometry: dict | None
    properties: dict
    measurement: object


@dataclass
class ParsedFile:
    crs_label: str
    features: list[ParsedFeature]


def _safe_extract(zip_path: Path, dest: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            if sum(i.file_size for i in zf.infolist()) > MAX_UNZIPPED_BYTES:
                raise InvalidGeoFile("Zip content too large")
            root = dest.resolve()
            for member in zf.infolist():
                target = (dest / member.filename).resolve()
                if not str(target).startswith(str(root)):  # zip-slip guard
                    raise InvalidGeoFile("Unsafe path inside zip")
            zf.extractall(dest)
    except zipfile.BadZipFile as exc:
        raise InvalidGeoFile("Not a valid zip file") from exc


def _json_safe(value):
    """Convert pandas/numpy values to JSON-serialisable Python values."""
    if isinstance(value, (list, dict)):
        return value
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    if hasattr(value, "isoformat"):  # datetime / Timestamp
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _read_shapefile_zip(path: Path, workdir: Path) -> gpd.GeoDataFrame:
    _safe_extract(path, workdir)
    shps = [p for p in workdir.rglob("*.shp") if not p.name.startswith("._")]
    if not shps:
        raise InvalidGeoFile("No .shp file found in the zip")
    frames = [gpd.read_file(p, engine="pyogrio") for p in shps]
    for shp, gdf in zip(shps, frames):
        if gdf.crs is None:
            raise InvalidGeoFile(f"{shp.name} has no CRS (.prj missing); cannot measure safely")
    base = frames[0].crs
    frames = [f.to_crs(base) for f in frames]
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


def _read_kml(path: Path) -> gpd.GeoDataFrame:
    layers = [row[0] for row in pyogrio.list_layers(path)]
    if not layers:
        raise InvalidGeoFile("KML contains no layers")
    frames = [gpd.read_file(path, layer=l, engine="pyogrio") for l in layers]
    frames = [f for f in frames if len(f)]
    if not frames:
        raise InvalidGeoFile("KML contains no features")
    gdf = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")  # KML is always WGS84


def parse_file(path: Path, workdir: Path) -> ParsedFile:
    suffix = path.suffix.lower()
    try:
        gdf = _read_shapefile_zip(path, workdir) if suffix == ".zip" else _read_kml(path)
    except InvalidGeoFile:
        raise
    except Exception as exc:  # corrupt/unreadable data from GDAL
        raise InvalidGeoFile(f"Could not read geospatial data: {exc}") from exc

    crs = CRS.from_user_input(gdf.crs)
    epsg = crs.to_epsg()
    crs_label = f"EPSG:{epsg}" if epsg else crs.name

    features = []
    prop_cols = [c for c in gdf.columns if c != gdf.geometry.name]
    for i, (_, row) in enumerate(gdf.iterrows()):
        geom = row[gdf.geometry.name]
        features.append(
            ParsedFeature(
                index=i,
                geometry_type=None if geom is None else geom.geom_type,
                geometry=None if geom is None else mapping(geom),
                properties={c: _json_safe(row[c]) for c in prop_cols},
                measurement=measure(geom, crs),
            )
        )
    return ParsedFile(crs_label=crs_label, features=features)
