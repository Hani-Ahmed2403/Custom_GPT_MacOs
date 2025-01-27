# Use the official Python image as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application code and requirements file into the container
COPY . .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "customgpt_draft:app"]
