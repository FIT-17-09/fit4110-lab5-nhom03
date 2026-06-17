"""
Mock AI service for FIT4110 Lab 05.

Endpoints:
- GET /health
- POST /predict

The implementation is intentionally lightweight: it returns a simple risk
classification based on sensor metric/value so the API can demonstrate an
end-to-end call to another service inside Docker Compose.
"""

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_NAME = "ai-service"
SERVICE_VERSION = "0.5.0-team-iot"


class PredictionRequest(BaseModel):
    device_id: str
    metric: str
    value: float
    unit: Optional[str] = None
    timestamp: str


class PredictionResponse(BaseModel):
    status: str
    risk_level: str
    confidence: float
    detail: str


app = FastAPI(
    title="FIT4110 Lab 05 - Mock AI Service",
    version=SERVICE_VERSION,
    description="Mock AI service used by IoT API in Docker Compose stack.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    risk = "low"
    confidence = 0.72
    detail = "normal sensor reading"

    if payload.metric == "temperature" and payload.value >= 70:
        risk = "high"
        confidence = 0.95
        detail = "temperature exceeds high threshold"
    elif payload.metric == "smoke" and payload.value > 0:
        risk = "critical"
        confidence = 0.98
        detail = "smoke detected"
    elif payload.metric == "motion" and payload.value > 0:
        risk = "medium"
        confidence = 0.86
        detail = "motion detected"

    return PredictionResponse(status="ok", risk_level=risk, confidence=confidence, detail=detail)
