.PHONY: help config setup lock format lint typecheck test test-integration test-evaluation test-e2e security verify run run-docker down logs

PYTHON ?= python3
BACKEND_VENV = backend/.venv
BACKEND_BIN = $(BACKEND_VENV)/bin
FRONTEND = frontend
ENV_FILE ?= config/app.env
COMPOSE = docker compose --env-file $(ENV_FILE)
LOAD_ENV = set -a && . ./$(ENV_FILE) && if [ -f .env ]; then . ./.env; fi && set +a

.DEFAULT_GOAL := help

help:
	@echo "Career Intelligence Assistant"
	@echo ""
	@echo "Run"
	@echo "  make setup              Copy config/app.env if missing; install Python and frontend deps"
	@echo "  make run                Host API + web dev server (does not start Docker)"
	@echo "  make run-docker         Compose Postgres, API and web; build images"
	@echo "  make down               Stop Compose services"
	@echo "  make logs               Follow Compose logs"
	@echo ""
	@echo "Check"
	@echo "  make lint               Ruff, mypy, TypeScript, ESLint"
	@echo "  make typecheck          Backend mypy and frontend tsc --noEmit"
	@echo "  make test               Hermetic backend and frontend unit tests"
	@echo "  make test-integration   Postgres/pgvector tests (PLAN phase 4)"
	@echo "  make test-evaluation    Fixture extraction and mapping baseline (PLAN phase 14)"
	@echo "  make test-e2e           Playwright walkthrough (PLAN phase 16)"
	@echo "  make security           Bandit, pip-audit, bun audit, Gitleaks, Trivy"
	@echo "  make verify             lint + test + security"
	@echo ""
	@echo "Also"
	@echo "  make format             Auto-fix Ruff and Prettier"
	@echo "  make lock               Regenerate backend/requirements*.lock with uv"
	@echo "  make config             Ensure config/app.env exists"
	@echo ""
	@echo "Settings: $(ENV_FILE) (copy from config/app.env.example). Optional root .env overlays host runs."
	@echo "Needs: Python 3.14, bun, Docker for run-docker/security."

config:
	test -f $(ENV_FILE) || cp config/app.env.example $(ENV_FILE)

setup: config
	$(PYTHON) -m venv $(BACKEND_VENV)
	$(BACKEND_BIN)/pip install -U pip
	$(BACKEND_BIN)/pip install -r backend/requirements-dev.lock
	$(BACKEND_BIN)/pip install --no-deps -e ./backend
	cd $(FRONTEND) && bun install --frozen-lockfile

# Two locks on purpose: the image installs requirements.lock and carries no
# test or audit tooling; make setup installs requirements-dev.lock.
lock:
	@command -v uv >/dev/null || (echo "lock needs uv: https://docs.astral.sh/uv/" && exit 1)
	cd backend && uv pip compile pyproject.toml --no-header -q -o requirements.lock
	cd backend && uv pip compile pyproject.toml --extra dev --no-header -q -o requirements-dev.lock

format:
	$(BACKEND_BIN)/ruff format backend/src backend/tests
	$(BACKEND_BIN)/ruff check --fix backend/src backend/tests
	cd $(FRONTEND) && bun run format

lint:
	$(BACKEND_BIN)/ruff check backend/src backend/tests
	$(BACKEND_BIN)/ruff format --check backend/src backend/tests
	cd backend && .venv/bin/mypy
	cd $(FRONTEND) && bun run typecheck
	cd $(FRONTEND) && bun run lint

typecheck:
	cd backend && .venv/bin/mypy
	cd $(FRONTEND) && bun run typecheck

# Hermetic: no database, no key, no model download.
test:
	cd backend && .venv/bin/pytest
	cd $(FRONTEND) && bun run test

test-integration:
	# Narrow Postgres suite; the default coverage gate does not apply to it.
	cd backend && .venv/bin/pytest -m integration -q --no-cov

test-evaluation:
	cd backend && .venv/bin/pytest tests/evaluation -q --no-cov

test-e2e:
	@test -d e2e/node_modules || (echo "Run: cd e2e && bun install" && exit 1)
	cd e2e && bunx playwright test

security:
	$(BACKEND_BIN)/bandit -r backend/src
	$(BACKEND_BIN)/pip-audit -r backend/requirements.lock
	$(BACKEND_BIN)/pip-audit -r backend/requirements-dev.lock
	cd $(FRONTEND) && bun audit --production
	docker run --rm -v "$(CURDIR):/src" -w /src ghcr.io/gitleaks/gitleaks:latest detect --source /src --no-git --verbose --config /src/.gitleaks.toml
	docker run --rm -v "$(CURDIR):/src" aquasec/trivy:latest fs --skip-dirs /src/frontend/node_modules --skip-dirs /src/backend/.venv --severity HIGH,CRITICAL --exit-code 1 /src

verify: lint test security

run-docker: config
	$(COMPOSE) up -d --build
	$(LOAD_ENV) && echo "Web http://localhost:$${WEB_PORT:-3000}  API http://localhost:$${API_PORT:-8000}/docs"

logs: config
	$(COMPOSE) logs -f

down: config
	$(COMPOSE) down

# Host API + web dev server. Uses your own Postgres from config/app.env.
# `alembic upgrade head` joins this target at PLAN phase 4.
run: config
	@test -x $(BACKEND_BIN)/uvicorn || (echo "Run make setup first." && exit 1)
	@command -v bun >/dev/null || (echo "run needs bun: https://bun.sh" && exit 1)
	$(LOAD_ENV) && \
	echo "Web http://localhost:3000  API http://localhost:8000/docs" && \
	trap 'kill 0' EXIT && \
	$(BACKEND_BIN)/uvicorn career_assistant.main:app --reload --host 127.0.0.1 --port 8000 & \
	cd $(FRONTEND) && bun run dev
