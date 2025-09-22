FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create embeddings directory with proper permissions
RUN mkdir -p /app/embeddings_db && \
    chmod 777 /app/embeddings_db

# Create non-root user
RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app

# Copy application code
COPY . .

# Switch to non-root user
USER myuser

# Add local bin to PATH
ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port 8080"]