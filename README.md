# Geospatial File Measurement API

FastAPI service that accepts a **Shapefile (.zip)** or **KML**, extracts every feature, and returns
**area (polygons)** and **length (lines)** in metres / square metres, calculated in a projected CRS.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs for interactive Swagger UI.

Run tests: `pytest -q`  |  Docker: `docker build -t geo-api . && docker run -p 8000:8000 geo-api`

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/files/` | Upload `.zip` (Shapefile) or `.kml` (multipart field `file`) and process it |
| GET | `/api/files/{id}/` | File info |
| GET | `/api/files/{id}/features/` | All features: index, geometry type, GeoJSON geometry, CRS, properties |
| GET | `/api/files/{id}/measurements/?skip=0&limit=1000` | Measurements per feature |
| GET | `/health` | Health check |

### Upload
```bash
curl -F "file=@tests/data/sample_survey.kml" http://127.0.0.1:8000/api/files/
```
```json
{"id":"3f1c...","filename":"sample_survey.kml","feature_count":3,"crs":"EPSG:4326","status":"COMPLETED","error":null,"created_at":"2026-10-07T10:00:00"}
```

### Measurements
```json
{
  "file_id": "3f1c...",
  "count": 3,
  "measurements": [
    {"index":0,"geometry_type":"Polygon","status":"OK","area_m2":1190457.3,"length_m":null,"measurement_crs":"EPSG:32643","note":null},
    {"index":1,"geometry_type":"LineString","status":"OK","area_m2":null,"length_m":1085.2,"measurement_crs":"EPSG:32643","note":null},
    {"index":2,"geometry_type":"Point","status":"NOT_APPLICABLE","area_m2":null,"length_m":null,"measurement_crs":null,"note":"No measurement defined for points"}
  ]
}
```

### Errors
`400` unsupported extension · `404` unknown id · `409` file not COMPLETED (e.g. FAILED, reason in message) · `413` file too large.
A corrupt file returns `201` with `status: "FAILED"` and an `error` message, so failures are inspectable later.

## Architecture

```
app/
  main.py            app + startup (creates tables)
  config.py          limits, paths
  database.py        SQLAlchemy engine/session (SQLite)
  models.py          GeoFile, Feature tables
  schemas.py         Pydantic response models
  api/files.py       HTTP layer only (validation, status codes)
  services/
    storage.py       stream upload to disk, size limit
    parser.py        zip-safe extract, read SHP/KML, normalise features
    crs.py           UTM zone selection + reprojection helpers
    measurements.py  area/length per geometry, never raises
    processing.py    orchestrates save -> parse -> measure -> persist
tests/               unit + API tests (KML, Shapefile in EPSG:4326 and EPSG:32643)
```

**File-processing flow:** validate extension -> create `GeoFile` row -> stream to `uploads/<id>/` ->
safe-extract zip / read KML layers with GDAL (pyogrio) -> build features -> measure -> save -> status `COMPLETED`/`FAILED`.

**Measurement flow:** source CRS -> WGS84 -> UTM zone of the *feature's centroid* -> `shapely` `.area` / `.length`.
Multi-geometries are summed. Points = `NOT_APPLICABLE`; GeometryCollection/empty = `UNSUPPORTED`; any exception = `ERROR` for that feature only.

**CRS handling:** original CRS is stored per feature. Degrees are never used for measurement.
Shapefiles without a `.prj` are rejected (guessing a CRS silently gives wrong numbers). KML is always EPSG:4326 by spec.

## Design Decisions

- **FastAPI over Django**: small, API-only service; automatic OpenAPI docs and Pydantic validation.
- **UTM per feature vs one CRS per file**: a file spanning several UTM zones still measures each feature in its own zone. Trade-off: accuracy degrades for very large features crossing zones.
  *Alternative considered:* geodesic calculation with `pyproj.Geod` (most accurate, no zone issues). A good future cross-check.
- **Synchronous processing**: simplest and fine for files up to 50 MB; status field already supports async.
- **SQLite + JSON columns**: zero setup. *Alternative:* PostgreSQL + PostGIS for spatial queries.
- **pyogrio/GDAL**: one reader for SHP and KML (incl. multiple KML folders/layers).
- **Security**: zip-slip check, unzipped-size cap, upload size cap, streaming writes.

## Learning
(Write your own: what you learned about CRS, why degrees are wrong for area, GDAL/KML quirks, testing geometry with known values.)

## Future Scope
- Background processing (Celery/RQ + Redis) with status polling
- PostGIS + spatial indexes; pagination on `/features/`
- Geodesic measurements and a `?crs=` override
- More formats: GeoJSON, GeoPackage; authentication; Docker Compose with Postgres
- Perimeter for polygons, centroid and bounding box per feature
