FROM python:3.13-slim

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install poetry==2.4.3

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main

COPY sph_backend/ ./sph_backend/

CMD ["uvicorn", "sph_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
