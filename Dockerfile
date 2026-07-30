FROM node:20-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS backend-build

RUN pip install --no-cache-dir poetry==2.0.0

WORKDIR /build/backend
COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry config virtualenvs.in-project true \
    && poetry install --only main --no-root --no-interaction --no-ansi


FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 app \
    && mkdir /data \
    && chown app:app /data

WORKDIR /app
COPY --from=backend-build /build/backend/.venv /opt/venv
COPY --chown=app:app backend/src ./src
COPY --from=frontend-build --chown=app:app /build/frontend/dist ./frontend

USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
