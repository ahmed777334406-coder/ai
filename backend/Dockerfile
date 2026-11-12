FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/backend/requirements.txt
ARG INSTALL_AI_DEPS=false
COPY backend/requirements-ai.txt /app/backend/requirements-ai.txt
RUN if [ "$INSTALL_AI_DEPS" = "true" ]; then pip install --no-cache-dir -r /app/backend/requirements-ai.txt; fi
COPY backend /app/backend
COPY scripts /app/scripts
COPY data /app/data
EXPOSE 8000
CMD ["sh", "-c", "alembic -c /app/backend/alembic.ini upgrade head && python /app/scripts/bootstrap.py && uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}"]
