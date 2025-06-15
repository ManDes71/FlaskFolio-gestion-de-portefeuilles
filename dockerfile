# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    sqlite3 \
    curl \
    cron && \
    apt-get clean  \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# Crée les dossiers nécessaires pour les volumes (au cas où ils n'existent pas encore)
RUN mkdir -p /app/db_data \
             /app/pea_trading/static/exports \
             /app/pea_trading/static/uploads



RUN pip install --upgrade pip &&  pip install --no-cache-dir -r requirements.txt

COPY cron_jobs.txt /tmp/cron_jobs
RUN crontab /tmp/cron_jobs

EXPOSE 5000

CMD ["bash", "-c", "python check_db.py && cron && gunicorn -w 1 -k gthread --threads 2 -b 0.0.0.0:5000 pea_trading:app"]
