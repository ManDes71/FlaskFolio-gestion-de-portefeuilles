# Dockerfile
FROM python:3.11-slim

# Variables d’environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

# CMD ["python", "app.py"]
CMD ["gunicorn", "-w", "1", "-k", "gthread", "--threads", "2", "-b", "0.0.0.0:5000", "pea_trading:app"]

