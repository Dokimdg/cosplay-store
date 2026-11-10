FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Жорстко прописані дані для суперкористувача напряму в Dockerfile
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@admin.com
ENV DJANGO_SUPERUSER_PASSWORD=GmanUoU_

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Команда автоматично застосує міграції та створить суперкористувача з вищевказаних змінних
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createsuperuser --noinput || true && gunicorn cosplay_store.wsgi:application --bind 0.0.0.0:8000"]