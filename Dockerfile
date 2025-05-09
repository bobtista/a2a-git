FROM python:3.11-slim

# Install UV and system dependencies
RUN apt-get update && \
    apt-get install -y git curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies with UV
RUN uv pip install --system .

# Expose the default port
EXPOSE 8052

# Run the agent
CMD ["python", "__main__.py", "--host", "0.0.0.0"] 