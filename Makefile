.PHONY: up down logs smoke test reset

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

smoke:
	./scripts/smoke.sh

test:
	cd mcp-server && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt && .venv/bin/pytest -q

reset:
	docker compose down -v --remove-orphans
