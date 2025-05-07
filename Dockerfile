FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3 python3-pip libpq-dev

# Copy the Flask application
COPY pyproject.toml .
COPY standard_pipelines/ standard_pipelines/
COPY migrations/ migrations/
COPY entrypoint.sh /entrypoint.sh
COPY flows.txt flows.txt
RUN mkdir /app/logs

RUN uv sync

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Expose Flask port
EXPOSE 5000

# Set environment variables if needed
ENV FLASK_ENV=development
ENV FLASK_APP=standard_pipelines
# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Set the default command
CMD ["uv", "run", "waitress-serve", "--port=5000", "--call", "standard_pipelines:create_app"]