FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY csms.py .
COPY config.py .
COPY rest_api.py .
COPY shared_store.py .

# Expose ports
EXPOSE 9000 8000

# Run both CSMS and REST API in the same process
CMD ["python", "csms.py"]
