# Multi-stage Dockerfile for CampusVerse: Builds React Frontend & Runs FastAPI Backend

# Stage 1: Build Vite React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend with Frontend Static Files
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for OCR and document handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend from Stage 1 into backend static directory
COPY --from=frontend-builder /app/frontend/dist ./frontend_dist

# Expose default port
ENV PORT=5000
EXPOSE 5000

# Start Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}"]
