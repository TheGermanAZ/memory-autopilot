FROM python:3.12-slim

WORKDIR /app

COPY 11labs-project/backend/requirements.deploy.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY 11labs-project/backend/ ./

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
