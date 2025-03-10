FROM python:3.8

WORKDIR /app

RUN python -m pip install flask gunicorn numpy pandas

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
