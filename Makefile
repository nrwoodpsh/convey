.PHONY: up down build logs lint typecheck test fmt

up:          ## 전체 기동
	docker compose up -d --build

down:        ## 전체 종료(볼륨 유지)
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f --tail=100

lint:
	ruff check .

fmt:
	ruff check --fix . && ruff format .

typecheck:
	mypy .

test:
	pytest
