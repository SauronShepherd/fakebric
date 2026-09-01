FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fakebric fakebric
COPY runtime-1.3.lock.json .
RUN useradd --create-home --uid 10001 fakebric && chown -R 10001:10001 /app
USER 10001
EXPOSE 8000
CMD ["uvicorn","fakebric.app:app","--host","0.0.0.0","--port","8000"]
