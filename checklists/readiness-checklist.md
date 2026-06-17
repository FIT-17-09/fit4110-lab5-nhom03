# Readiness Checklist – Lab 05

- [x] **Database ready:** container `fit4110-db-lab05` chạy PostgreSQL và có healthcheck `pg_isready`.
- [x] **AI service ready:** container `fit4110-ai-lab05` có endpoint `GET /health` và `POST /predict`.
- [x] **API ready:** container `fit4110-api-lab05` có `GET /health`, `POST /readings`, `GET /readings/latest`, `GET /readings/{reading_id}`.
- [x] **API kết nối DB:** API lưu sensor reading vào PostgreSQL.
- [x] **API kết nối AI:** khi tạo reading, API gọi `http://ai-service:9000/predict` và trả `ai_result`.
- [x] **Environment variables:** cấu hình runtime nằm trong `.env.example`; không commit secret thật.
- [x] **Network:** các service giao tiếp nội bộ qua network `team-internal`; API tham gia thêm network `class-net` theo yêu cầu Lab 05.
- [x] **Healthcheck:** API, DB và AI đều có healthcheck trong `docker-compose.yml`.
- [x] **Non-root:** API chạy bằng user non-root trong Dockerfile.
- [x] **Image tag:** image API được tag `fit4110-lab5-nhom03-iot-api:v0.1.0-team-iot`.

## Evidence cần chụp khi nộp

- `docker compose ps`
- `curl http://localhost:8000/health`
- `curl http://localhost:9000/health`
- `docker exec -it fit4110-db-lab05 pg_isready -U lab05 -d iotdb`
- kết quả `POST /readings`
- kết quả `npm run test:compose`
