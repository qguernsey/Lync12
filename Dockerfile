FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8080

CMD ["python3", "start.py"]
