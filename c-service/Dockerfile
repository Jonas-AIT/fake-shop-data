FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libcurl4-openssl-dev \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ENV TZ = Europe/Vienna   

RUN pip install --break-system-packages flask
RUN pip install --break-system-packages flask gunicorn

WORKDIR /app

COPY statusabfrage.c /app/
RUN gcc -O2 -o /app/statusabfrage /app/statusabfrage.c -lcurl

COPY check_watchlist.sh /app/
RUN chmod +x /app/check_watchlist.sh

COPY c-wrapper.py /app/

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "c-wrapper:app"]