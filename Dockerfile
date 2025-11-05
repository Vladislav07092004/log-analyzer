FROM python:2.7.18-slim

WORKDIR /app

# Копируем все файлы в контейнер
COPY . .

# Устанавливаем переменные окружения для поддержки русского языка
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

CMD ["python", "main.py"]