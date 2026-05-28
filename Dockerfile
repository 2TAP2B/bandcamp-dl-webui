FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install bandcamp-dl first (layer cache-friendly)
COPY pyproject.toml ./pyproject.toml
COPY bandcamp_dl/ ./bandcamp_dl/
RUN pip install --no-cache-dir -e .

# Install Flask
RUN pip install --no-cache-dir flask

# Copy webui
COPY webui/ ./webui/

ENV DOWNLOAD_DIR=/downloads
EXPOSE 5000

CMD ["python", "webui/app.py"]
