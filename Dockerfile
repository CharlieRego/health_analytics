FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY dbt/ dbt/
RUN dbt deps --project-dir dbt --profiles-dir dbt

COPY pipeline/ pipeline/

CMD ["python", "-m", "pipeline.main"]
