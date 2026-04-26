FROM python:3.11-slim

WORKDIR /app

# curl is used by the healthcheck below; ca-certificates is needed for any
# outbound HTTPS calls (e.g. future AIMS API integration in Sprint 6).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data/ is mounted as a volume in production so runs.db survives restarts.
RUN mkdir -p data config && chown -R 1000:1000 /app
USER 1000:1000

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
