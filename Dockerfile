FROM python:3.12-slim

WORKDIR /app

COPY deploy/max-ca/*.crt /usr/local/share/ca-certificates/
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY era_bot ./era_bot
COPY max_bot ./max_bot
COPY main.py main_max.py ./

VOLUME ["/app/data"]
ENV SUBSCRIBERS_FILE=/app/data/subscribers.json
ENV MAX_SUBSCRIBERS_FILE=/app/data/max_subscribers.json
ENV MAX_STATE_FILE=/app/data/max_state.json

CMD ["python", "main.py"]
