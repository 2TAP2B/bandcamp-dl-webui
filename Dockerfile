FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://git.steltner.cloud/2tap2b/bandcamp-dl-webui

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -u 1000 -m -s /bin/sh appuser

WORKDIR /app

# Copy and install bandcamp-dl first (layer cache-friendly)
COPY pyproject.toml ./pyproject.toml
COPY bandcamp_dl/ ./bandcamp_dl/
RUN pip install --no-cache-dir -e .

# Install Flask
RUN pip install --no-cache-dir flask

# Copy webui
COPY webui/ ./webui/

RUN mkdir -p /downloads && chown appuser:appuser /downloads

ENV DOWNLOAD_DIR=/downloads
EXPOSE 5000

USER appuser
CMD ["python", "webui/app.py"]
