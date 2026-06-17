# FIT4110 Lab 05 - Docker Compose Readiness

**Nhóm:** Nhóm 03  
**Service:** IoT Ingestion Service  
**Học phần:** FIT4110 – Dịch vụ kết nối và Công nghệ nền tảng  
**Buổi 5:** Điều phối đa dịch vụ với Docker Compose, readiness & AI service

Repo này được hoàn thiện theo form Lab 05 của cô: từ Lab 04 Docker container đơn lẻ, mở rộng thành stack nhiều service chạy bằng Docker Compose.

## 1. Kiến trúc stack

Lab 05 định nghĩa 3 container chính:

| Service | Container | Port | Vai trò |
|---|---|---:|---|
| API | `fit4110-api-lab05` | 8000 | FastAPI IoT Ingestion, nhận/lưu sensor reading |
| DB | `fit4110-db-lab05` | nội bộ | PostgreSQL lưu dữ liệu readings |
| AI | `fit4110-ai-lab05` | 9000 | Mock AI service, trả risk level khi API gọi `/predict` |

Luồng end-to-end:

```text
Client/Postman
  ↓
IoT API /readings
  ↓
PostgreSQL lưu reading
  ↓
AI service /predict
  ↓
API trả response có ai_result
```

## 2. Endpoint chính

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| GET | `/health` | Không | Kiểm tra API, DB, AI |
| POST | `/readings` | Bearer token | Tạo sensor reading |
| GET | `/readings/latest?limit=5` | Bearer token | Lấy readings mới nhất |
| GET | `/readings/{reading_id}` | Bearer token | Lấy chi tiết reading |
| GET | `http://localhost:9000/health` | Không | Health AI service |
| POST | `http://localhost:9000/predict` | Không | Mock prediction |

Token mặc định:

```text
Authorization: Bearer local-dev-token
```

## 3. Chạy nhanh

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Kiểm tra health:

```bash
curl http://localhost:8000/health
curl http://localhost:9000/health
docker exec -it fit4110-db-lab05 pg_isready -U lab05 -d iotdb
```

## 4. Test nhanh bằng curl

```bash
curl -X POST http://localhost:8000/readings \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32-LAB-A01","metric":"temperature","value":31.5,"unit":"celsius","timestamp":"2026-05-13T08:30:00+07:00"}'
```

Lấy dữ liệu:

```bash
curl -H "Authorization: Bearer local-dev-token" "http://localhost:8000/readings/latest?limit=5"
```

## 5. Chạy Newman

```bash
npm install
npm run test:compose
```

Report sinh ra:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

## 6. Artefact Lab 05

- `docker-compose.yml`
- `.dockerignore`
- `.env.example`
- `RUN_COMPOSE.md`
- `contracts/iot-ingestion.openapi.yaml`
- `postman/collections/FIT4110_lab05_iot_compose.postman_collection.json`
- `postman/environments/FIT4110_lab05_local.postman_environment.json`
- `checklists/readiness-checklist.md`
- `reports/`

## 7. Ghi chú

- API container chạy bằng user non-root trong Dockerfile.
- Compose dùng healthcheck cho API, DB và AI.
- Runtime config nằm trong `.env.example`, không commit secret thật.
- Image tag gợi ý: `fit4110-lab5-nhom03-iot-api:v0.1.0-team-iot`.
