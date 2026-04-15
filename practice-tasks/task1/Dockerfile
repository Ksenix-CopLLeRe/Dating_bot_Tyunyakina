FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y sqlite3

RUN mkdir -p /app/data && chmod 777 /app/data

CMD ["python", "main.py"]