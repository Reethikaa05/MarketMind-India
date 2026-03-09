FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure the database directory is writable
RUN touch portfolio.db && chmod 666 portfolio.db

# Expose the port for the SSE transport
EXPOSE 8000

# Run the server using the MCP CLI with SSE transport
# This allows Claude to connect via a URL instead of a local process
CMD ["python", "-m", "mcp", "run", "server.py", "--transport", "sse", "--port", "8000"]
