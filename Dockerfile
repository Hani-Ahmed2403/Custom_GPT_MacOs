# Use a prebuilt base image with Tesseract and Poppler
FROM jbarlow83/ocrmypdf:latest

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
