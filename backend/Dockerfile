# Build the virtual environment in one stage, ship it in a clean one.
# The runtime image contains no pip, no compiler and no development tools.
FROM python:3.13-slim-bookworm AS build

WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml requirements.lock ./
COPY src ./src

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock \
    && /opt/venv/bin/pip install --no-cache-dir --no-deps .

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --system --create-home --uid 10001 career

COPY --from=build /opt/venv /opt/venv

WORKDIR /app
USER career

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD python -c "import urllib.request as u, sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"

# `alembic upgrade head &&` joins this command at PLAN.md phase 4, when there is
# a schema to migrate. Until then the API owns no database.
CMD ["uvicorn", "career_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"]
