FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The base image already contains playwright browsers and OS dependencies!
# We just need to copy our code.
COPY . .

# Run the FastAPI server
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
