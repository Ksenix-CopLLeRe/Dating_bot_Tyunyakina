FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y sqlite3

CMD ["python", "main.py"]