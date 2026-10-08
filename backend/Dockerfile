# Build the virtual environment in one stage, ship it in a clean one.
# The runtime image contains no pip, no compiler and no development tools.
FROM python:3.14-slim-bookworm AS build

WORKDIR /app/backend
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY backend/pyproject.toml backend/requirements.lock ./
COPY backend/src ./src

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock \
    && /opt/venv/bin/pip install --no-cache-dir --no-deps .

FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/backend/src"

RUN useradd --system --create-home --uid 10001 career

COPY --from=build /opt/venv /opt/venv
COPY backend/src /app/backend/src
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/migrations /app/backend/migrations
COPY config/models.toml config/scoring_rubric.toml /app/config/

WORKDIR /app/backend
USER career

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD python -c "import urllib.request as u, sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/ready', timeout=2).status == 200 else 1)"

CMD ["python", "-m", "career_assistant.adapters.persistence.startup"]
