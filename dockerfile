# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Paris

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    sqlite3 \
    curl \
    cron \
    procps \
    tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Créer les répertoires pour les volumes avant de copier les fichiers
RUN mkdir -p /app/db_data \
    && mkdir -p /app/pea_trading/static/logs \
    && mkdir -p /app/pea_trading/static/exports \
    && mkdir -p /app/pea_trading/static/uploads

COPY . /app

RUN pip install --upgrade pip &&  pip install --no-cache-dir -r requirements.txt

COPY cron_jobs.txt /tmp/cron_jobs
RUN crontab /tmp/cron_jobs

EXPOSE 5000

CMD ["bash", "-c", "python check_db.py && service cron start && gunicorn -w 1 -k gthread --threads 2 -b 0.0.0.0:5000 pea_trading:app"]
