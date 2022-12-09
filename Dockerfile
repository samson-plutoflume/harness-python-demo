FROM python:3.9-slim-buster

ENV HARNESS_BASE_URL="https://config.ff.harness.io/api/1.0" \
  HARNESS_EVENT_URL="https://events.ff.harness.io/api/1.0" \
  HARNESS_POLL_INTERVAL=10

WORKDIR /app

COPY ./ .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
