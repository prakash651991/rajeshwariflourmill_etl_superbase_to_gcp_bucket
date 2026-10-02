FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 main:app