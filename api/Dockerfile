FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY alembic.ini openapi.yaml ./
COPY alembic ./alembic
COPY scripts ./scripts

EXPOSE 8000
# Sin estado en memoria: se pueden levantar N réplicas detrás del balanceador (RNF-REN-03).
CMD ["uvicorn", "pokearena.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
