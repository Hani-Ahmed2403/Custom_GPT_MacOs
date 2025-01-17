# Use a compatible Python base image
FROM python:3.10-bullseye as builder

# Install Tesseract OCR and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libtesseract-dev poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.10-bullseye

# Copy installed dependencies and files from the builder stage
COPY --from=builder /usr /usr
COPY --from=builder /app /app

# Set working directory
WORKDIR /app

# Expose the application port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "-b", "0.0.0.0:5000", "custom_gpt_api:app"]
