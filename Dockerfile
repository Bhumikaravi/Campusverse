FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for OCR and document handling (Debian 12 compatible)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy pre-built frontend distribution directly
COPY frontend/dist ./frontend_dist

# Default port
ENV PORT=5000
EXPOSE 5000

# Start Uvicorn bound to Railway's assigned port
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}"]
