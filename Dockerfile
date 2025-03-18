# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the script and dependencies
COPY requirements.txt ./
COPY tempest-proxy.py ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the script listens on
EXPOSE 8080

# Run the application
CMD ["uvicorn", "orbs-proxy:app", "--host", "0.0.0.0", "--port", "8080", "--reload", "--forwarded-allow-ips=*", "--proxy-headers"]

# For better performance, we can use Gunicorn with multiple workers:
# Add "gunicorn" to requirements and enable this instead of the other CMD
# But this will not auto-reload on a change of the .py file
#CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "--workers", "4", "--forwarded-allow-ips", "*", "--proxy-headers", "tempest-proxy:app"]

# Use this for dev with gunicorn (auto-reload is only recommended for dev not prod)
#CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "--reload", "--workers", "4", "--forwarded-allow-ips", "*", "--proxy-headers", "tempest-proxy:app"]
