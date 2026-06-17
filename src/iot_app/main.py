import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import psycopg
from psycopg.types.json import Jsonb
import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0-team-iot")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "iotdb")
DB_USER = os.getenv("POSTGRES_USER", "lab05")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lab05pass")

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:9000")

app = FastAPI(
    title="FIT4110 Lab 05 - IoT Ingestion Service",
    version=SERVICE_VERSION,
    description=(
        "IoT Ingestion API chạy trong Docker Compose. API nhận sensor reading, "
        "lưu PostgreSQL, gọi AI service mock và hỗ trợ kiểm thử Newman end-to-end."
    ),
)


class SensorMetric(str, Enum):
    temperature = "temperature"
    humidity = "humidity"
    motion = "motion"
    smoke = "smoke"


class SensorUnit(str, Enum):
    celsius = "celsius"
    percent = "percent"
    boolean = "boolean"
    ppm = "ppm"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    db: str
    ai_service: str


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., min_length=3, examples=["ESP32-LAB-A01"])
    metric: SensorMetric = Field(..., examples=["temperature"])
    value: float = Field(
        ...,
        ge=-40,
        le=80,
        description="Boundary range used in Lab 03/Lab 04: -40 đến 80.",
        examples=[31.5],
    )
    unit: Optional[SensorUnit] = Field(default=None, examples=["celsius"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class SensorReading(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    value: float
    unit: Optional[SensorUnit] = None
    timestamp: str
    created_at: str
    ai_result: Optional[Dict] = None


class SensorReadingCreated(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    accepted: bool
    created_at: str
    ai_result: Optional[Dict] = None


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )
    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))
    return JSONResponse(status_code=exc.status_code, content=problem, media_type="application/problem+json")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )
    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_conn():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True,
    )


def init_db():
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id SERIAL PRIMARY KEY,
                reading_id TEXT UNIQUE NOT NULL,
                device_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                unit TEXT,
                reading_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ai_result JSONB
            )
            """
        )


@app.on_event("startup")
def startup():
    init_db()


def next_reading_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sensor_readings WHERE reading_id LIKE %s", (f"R-{today}-%",))
        count = cur.fetchone()[0]
    return f"R-{today}-{count + 1:04d}"


def call_ai(payload: SensorReadingCreate) -> Dict:
    try:
        res = requests.post(
            f"{AI_SERVICE_URL}/predict",
            json={
                "device_id": payload.device_id,
                "metric": payload.metric.value,
                "value": payload.value,
                "unit": payload.unit.value if payload.unit else None,
                "timestamp": payload.timestamp,
            },
            timeout=3,
        )
        res.raise_for_status()
        return res.json()
    except Exception as ex:
        return {"status": "unavailable", "detail": str(ex)}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = "ok"
    ai_status = "ok"
    try:
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:
        db_status = "error"
    try:
        ai_res = requests.get(f"{AI_SERVICE_URL}/health", timeout=2)
        if ai_res.status_code != 200:
            ai_status = "error"
    except Exception:
        ai_status = "error"
    return HealthResponse(
        status="ok" if db_status == "ok" and ai_status == "ok" else "degraded",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        db=db_status,
        ai_service=ai_status,
    )


@app.post(
    "/readings",
    response_model=SensorReadingCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}, 422: {"model": ProblemDetails}, 429: {"model": ProblemDetails}},
)
def create_reading(payload: SensorReadingCreate, response: Response) -> SensorReadingCreated:
    if payload.metric == SensorMetric.temperature and payload.value >= 70:
        response.headers["X-Warning"] = "high-temperature"

    reading_id = next_reading_id()
    created_at = now_iso()
    ai_result = call_ai(payload)

    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sensor_readings
            (reading_id, device_id, metric, value, unit, reading_timestamp, created_at, ai_result)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                reading_id,
                payload.device_id,
                payload.metric.value,
                payload.value,
                payload.unit.value if payload.unit else None,
                payload.timestamp,
                created_at,
                Jsonb(ai_result),
            ),
        )

    return SensorReadingCreated(
        reading_id=reading_id,
        device_id=payload.device_id,
        metric=payload.metric,
        accepted=True,
        created_at=created_at,
        ai_result=ai_result,
    )


@app.get("/readings/latest", dependencies=[Depends(verify_bearer_token)])
def latest_readings(device_id: Optional[str] = Query(default=None), limit: int = Query(default=10, ge=1, le=100)) -> Dict[str, List[Dict]]:
    query = """
        SELECT reading_id, device_id, metric, value, unit, reading_timestamp AS timestamp, created_at, ai_result
        FROM sensor_readings
    """
    params = []
    if device_id:
        query += " WHERE device_id=%s"
        params.append(device_id)
    query += " ORDER BY id DESC LIMIT %s"
    params.append(limit)
    with db_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
    return {"items": rows}


@app.get("/readings/{reading_id}", dependencies=[Depends(verify_bearer_token)])
def get_reading(reading_id: str) -> Dict:
    with db_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT reading_id, device_id, metric, value, unit, reading_timestamp AS timestamp, created_at, ai_result
            FROM sensor_readings WHERE reading_id=%s
            """,
            (reading_id,),
        )
        item = cur.fetchone()
    if item:
        return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Reading {reading_id} does not exist",
            instance=f"/readings/{reading_id}",
            problem_type="https://smart-campus.local/problems/not-found",
        ),
    )
