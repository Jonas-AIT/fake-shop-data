FROM debian:bookworm-slim

# System-Pakete inkl. Build-Tools für libpostal installieren
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    git \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libcurl4-openssl-dev \
    libsqlite3-dev \
    python3 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# libpostal C-Bibliothek bauen
RUN git clone https://github.com/openvenues/libpostal /tmp/libpostal \
    && cd /tmp/libpostal \
    && ./bootstrap.sh \
    && ./configure --datadir=/var/lib/libpostal \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && rm -rf /tmp/libpostal

ENV TZ=Europe/Vienna   

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --break-system-packages -r /app/requirements.txt
RUN playwright install chromium --with-deps

# C-Code aus c-service kopieren & kompilieren
COPY c-service/statusabfrage.c /app/
RUN gcc -O2 -o /app/statusabfrage /app/statusabfrage.c -lcurl -lsqlite3

# Skript & Python-Dateien kopieren
COPY c-service/check_watchlist.sh /app/check_watchlist.sh
RUN chmod +x /app/check_watchlist.sh
COPY c-service/c-wrapper.py /app/c-wrapper.py
COPY shop-data.py /app/shop-data.py

CMD ["gunicorn", "-t", "120", "-w", "1", "-b", "0.0.0.0:8000", "c-wrapper:app"]