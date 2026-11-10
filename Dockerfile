FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо Python-залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо проєкт
COPY . /app/

# Збираємо статику під час білду
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Запуск через Gunicorn
CMD ["gunicorn", "cosplay_store.wsgi:application", "--bind", "0.0.0.0:8000"]