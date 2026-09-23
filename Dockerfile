FROM python:3.13-slim

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false

RUN useradd --create-home --uid 1000 sphuser \
    && mkdir -p /app/data \
    && chown sphuser:sphuser /app/data

RUN pip install poetry==2.4.3

COPY pyproject.toml poetry.lock /app/
RUN poetry install --only main

COPY sph_backend/ /app/sph_backend/

EXPOSE 8000

USER sphuser
CMD ["uvicorn", "sph_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
