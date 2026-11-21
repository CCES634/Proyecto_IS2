# ---------- Etapa 1: construcción de dependencias ----------
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final liviana ----------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --system --uid 1001 app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app
COPY wsgi.py .
USER app
EXPOSE 5000
CMD ["gunicorn", "--preload", "--workers", "2", "--threads", "4", "--worker-class", "gthread", "--keep-alive", "75", "--bind", "0.0.0.0:5000", "wsgi:app"]
