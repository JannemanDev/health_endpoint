FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user and change ownership with proper permissions
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    chmod -R u+r /app && \
    chmod u+x /app && \
    chmod u+x /app/health_server.py
USER appuser

EXPOSE 8000
CMD ["python3", "health_server.py"]
