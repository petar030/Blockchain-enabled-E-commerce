FROM python:3.12-slim-bookworm

WORKDIR /app

# Ako ti ne trebaju C ekstenzije, dovoljno je minimalno okruženje
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "api.py"]
