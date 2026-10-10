FROM python:3.13.16-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY support_mcp ./support_mcp
COPY kb ./kb

RUN useradd --system --uid 10001 app && mkdir -p /data && chown app:app /data
USER app

ENV SUPPORT_DB_PATH=/data/support.db \
    SUPPORT_KB_DIR=/app/kb \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000
CMD ["python", "-m", "support_mcp.server"]
