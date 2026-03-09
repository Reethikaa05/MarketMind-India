FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure the database directory is writable
RUN touch portfolio.db && chmod 666 portfolio.db

# Expose the port for the SSE transport
EXPOSE 8000

# Run the server using the python command directly. 
# The server.py is now smart enough to detect the PORT environment variable
# and start as an SSE server on 0.0.0.0.
CMD ["python", "server.py"]
