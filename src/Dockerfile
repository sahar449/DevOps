###############################
# Stage 1: Build Dependencies
###############################
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

###############################
# Stage 2: Production (Alpine)
###############################
FROM python:3.12-alpine

# Create non-root user with UID 1000
RUN adduser -D -u 1000 -h /home/appuser -s /bin/sh appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY app.py .

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]