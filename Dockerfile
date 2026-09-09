FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY *.py ./
COPY templates/ ./templates/

CMD ["python", "server.py"]
