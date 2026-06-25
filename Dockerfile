FROM python:3.13-slim

WORKDIR /app

# Install basic system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Copy project specification files
COPY pyproject.toml uv.lock ./

# Install dependencies via uv
RUN uv sync --frozen --no-dev

# Copy the backend source code and entrypoint
COPY backend ./backend
COPY main.py ./

# Expose backend port
EXPOSE 8000

# Set required environment variables
ENV HOST=0.0.0.0
ENV PORT=8000

# Run the backend application
CMD ["uv", "run", "main.py"]
