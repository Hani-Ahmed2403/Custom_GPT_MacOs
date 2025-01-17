# Use a lightweight Python base image
FROM python:3.10-slim

# Install system dependencies, including Tesseract OCR and Poppler utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libtesseract-dev poppler-utils && \
    apt-get install -y python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy all project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask app port
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "-b", "0.0.0.0:5000", "custom_gpt_api:app"]
