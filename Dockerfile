FROM python:3.12-slim

# python:3.12-slim ships pip 25.0.1, whose vendored certifi still trusts the compromised
# eMudhra intermediates (Oct 2026). Verify against the patched Debian store, then upgrade pip.
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt
RUN pip install --no-cache-dir 'pip>=26.2.2'

WORKDIR /app

COPY 11labs-project/backend/requirements.deploy.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY 11labs-project/backend/ ./

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
