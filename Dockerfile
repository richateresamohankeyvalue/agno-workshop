FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
