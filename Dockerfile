FROM python:3.11-slim

WORKDIR /app

COPY libcal/ libcal/
COPY requirements.txt ./

RUN python -m pip install --upgrade pip && \
    SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 python -m pip install -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/libcal

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
