# RUN_COMPOSE.md – Hướng dẫn chạy Lab 05

## 1. Chuẩn bị

Yêu cầu:

- Docker Desktop hoặc Docker Engine có Compose v2
- Node.js 20.x nếu muốn chạy Newman
- Git

## 2. Tạo file môi trường

```bash
cp .env.example .env
```

Trên PowerShell:

```powershell
copy .env.example .env
```

Không commit `.env` thật lên Git.

## 3. Chạy stack Compose

```bash
docker compose up -d --build
```

Stack gồm:

- `fit4110-db-lab05`: PostgreSQL
- `fit4110-ai-lab05`: Mock AI service
- `fit4110-api-lab05`: IoT Ingestion API

## 4. Kiểm tra readiness

```bash
docker compose ps
```

API:

```bash
curl http://localhost:8000/health
```

AI:

```bash
curl http://localhost:9000/health
```

DB:

```bash
docker exec -it fit4110-db-lab05 pg_isready -U lab05 -d iotdb
```

Kết quả mong muốn: các container đều `healthy`.

## 5. Test end-to-end bằng curl

Tạo reading:

```bash
curl -X POST http://localhost:8000/readings \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32-LAB-A01","metric":"temperature","value":31.5,"unit":"celsius","timestamp":"2026-05-13T08:30:00+07:00"}'
```

Trên PowerShell có thể dùng:

```powershell
$headers = @{
  "Authorization" = "Bearer local-dev-token"
  "Content-Type" = "application/json"
}

$body = @{
  device_id = "ESP32-LAB-A01"
  metric = "temperature"
  value = 31.5
  unit = "celsius"
  timestamp = "2026-05-13T08:30:00+07:00"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/readings" -Method POST -Headers $headers -Body $body
```

Lấy readings mới nhất:

```bash
curl -H "Authorization: Bearer local-dev-token" "http://localhost:8000/readings/latest?limit=5"
```

## 6. Chạy Newman

```bash
npm install
npm run test:compose
```

Report:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

## 7. Xem log

```bash
docker compose logs -f
```

## 8. Dừng stack

```bash
docker compose down
```

Xóa cả volume DB:

```bash
docker compose down -v
```

## 9. Lệnh Makefile

```bash
make compose-up
make logs
make test-compose
make compose-down
```
