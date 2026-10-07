from fastapi import FastAPI

app = FastAPI(title="Geospatial File Measurement API", version="1.0.0")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
