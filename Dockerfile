FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY harvester/ harvester/

CMD ["python", "-m", "harvester.main"]
