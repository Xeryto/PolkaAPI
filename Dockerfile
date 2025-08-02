# Stage 1: Builder - Install dependencies
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies for certain Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final Image - Production
FROM python:3.10-slim

WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser

# Copy installed dependencies from the builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies from local wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Set the default command to run the application
# This command is suitable for production and runs the app on 0.0.0.0:8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
