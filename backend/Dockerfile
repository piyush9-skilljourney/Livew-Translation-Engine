# Use an official lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for audio processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create static directory for the frontend
RUN mkdir -p static

# Copy application code
COPY . .


# Expose the port FastAPI will run on
EXPOSE 8080

# Command to run the application using uvicorn
# We use 8080 as it is the default for Google Cloud Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
