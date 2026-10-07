import pytest


def upload(client, name, data, ctype="application/octet-stream"):
    return client.post("/api/files/", files={"file": (name, data, ctype)})


def test_kml_upload_and_measurements(client, kml_bytes):
    r = upload(client, "survey.kml", kml_bytes)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["feature_count"] == 3
    assert body["crs"] == "EPSG:4326"

    info = client.get(f"/api/files/{body['id']}/").json()
    assert info["filename"] == "survey.kml"

    m = client.get(f"/api/files/{body['id']}/measurements/").json()["measurements"]
    by_type = {x["geometry_type"]: x for x in m}
    # 0.01deg x 0.01deg at ~13N is ~1.19 km2 -- NOT 0.0001 (degrees^2)
    assert by_type["Polygon"]["area_m2"] == pytest.approx(1_190_000, rel=0.02)
    assert by_type["LineString"]["length_m"] == pytest.approx(1_085, rel=0.02)
    assert by_type["Polygon"]["measurement_crs"] == "EPSG:32643"
    assert by_type["Point"]["status"] == "NOT_APPLICABLE"
    assert by_type["Point"]["area_m2"] is None


def test_features_endpoint(client, kml_bytes):
    fid = upload(client, "a.kml", kml_bytes).json()["id"]
    feats = client.get(f"/api/files/{fid}/features/").json()["features"]
    assert len(feats) == 3
    assert feats[0]["geometry"]["type"] == "Polygon"
    assert feats[0]["properties"]["Name"] == "Plot A"


def test_shapefile_4326_and_projected_agree(client, shp_zip_4326, shp_zip_utm):
    areas = []
    for z in (shp_zip_4326, shp_zip_utm):
        r = upload(client, z.name, z.read_bytes(), "application/zip").json()
        assert r["status"] == "COMPLETED"
        m = client.get(f"/api/files/{r['id']}/measurements/").json()["measurements"]
        areas.append(m[0]["area_m2"])
    assert areas[0] == pytest.approx(areas[1], rel=1e-3)  # same land, same area


def test_unsupported_extension(client):
    assert upload(client, "x.txt", b"hello").status_code == 400


def test_bad_zip_marks_failed(client):
    r = upload(client, "bad.zip", b"not a zip").json()
    assert r["status"] == "FAILED"
    assert "zip" in r["error"].lower()
    assert client.get(f"/api/files/{r['id']}/measurements/").status_code == 409


def test_unknown_id_404(client):
    assert client.get("/api/files/doesnotexist/").status_code == 404
