import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, Polygon

# isolate DB + uploads before importing the app
_tmp = Path(tempfile.mkdtemp())
os.environ["GEO_TEST_DIR"] = str(_tmp)

from app import config  # noqa: E402

config.UPLOAD_DIR = _tmp / "uploads"
config.DATABASE_URL = f"sqlite:///{_tmp / 'test.db'}"

from app import database  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

database.engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
database.SessionLocal = sessionmaker(bind=database.engine, expire_on_commit=False)

from app.main import app  # noqa: E402
from app.api import files as files_api  # noqa: E402
from app.services import storage  # noqa: E402

storage.UPLOAD_DIR = config.UPLOAD_DIR
database.Base.metadata.create_all(database.engine)


def _override_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[database.get_db] = _override_db


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


# ~0.01 deg x 0.01 deg square near Bengaluru (~1.19 km2)
SQUARE = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98)])
LINE = LineString([(77.59, 12.97), (77.60, 12.97)])  # ~1.08 km east-west


KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Plot A</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
77.59,12.97,0 77.60,12.97,0 77.60,12.98,0 77.59,12.98,0 77.59,12.97,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
<Placemark><name>Road</name><LineString><coordinates>77.59,12.97,0 77.60,12.97,0</coordinates></LineString></Placemark>
<Placemark><name>Gate</name><Point><coordinates>77.595,12.975,0</coordinates></Point></Placemark>
</Document></kml>"""


@pytest.fixture()
def kml_bytes():
    return KML.encode()


def make_shapefile_zip(path: Path, crs: str) -> Path:
    gdf = gpd.GeoDataFrame(
        {"name": ["plot", "road"]},
        geometry=[SQUARE, LINE],
        crs="EPSG:4326",
    ).to_crs(crs)
    # shapefiles hold one geometry type per file -> write polygons and lines separately is the norm;
    # here we keep polygons only, plus a separate points layer test below.
    gdf = gdf.iloc[[0]]
    folder = path / "shp"
    folder.mkdir(parents=True, exist_ok=True)
    gdf.to_file(folder / "plots.shp")
    zpath = path / f"plots_{crs.replace(':', '')}.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in folder.iterdir():
            zf.write(f, f.name)
    shutil.rmtree(folder)
    return zpath


@pytest.fixture()
def shp_zip_4326(tmp_path):
    return make_shapefile_zip(tmp_path, "EPSG:4326")


@pytest.fixture()
def shp_zip_utm(tmp_path):
    return make_shapefile_zip(tmp_path, "EPSG:32643")
