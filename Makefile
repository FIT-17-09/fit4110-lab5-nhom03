.PHONY: install lint build run compose-up compose-down logs test-compose

install:
	npm install

lint:
	npx spectral lint contracts/*.yaml

build:
	docker build -t fit4110-lab5-nhom03-iot-api:v0.1.0-team-iot .

run:
	docker run --rm --name fit4110-api-lab05 -p 8000:8000 --env-file .env.example fit4110-lab5-nhom03-iot-api:v0.1.0-team-iot

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

logs:
	docker compose logs -f

test-compose:
	npm run test:compose
