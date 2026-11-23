FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOAD_TEMP_DIR=/tmp/vps-lab

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN mkdir -p /tmp/vps-lab
EXPOSE 8000
CMD ["python", "-m", "app"]

