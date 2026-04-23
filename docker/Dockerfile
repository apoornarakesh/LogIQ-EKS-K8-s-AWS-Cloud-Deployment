FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/nextgen_dashboard.py .

EXPOSE 8000

CMD ["uvicorn", "nextgen_dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
