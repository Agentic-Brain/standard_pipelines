FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3 python3-pip libpq-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application
COPY standard_pipelines/ standard_pipelines/
COPY migrations/ migrations/
COPY entrypoint.sh /entrypoint.sh
RUN mkdir /app/logs

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
CMD ["waitress-serve", "--port=5000", "--call", "standard_pipelines:create_app"]