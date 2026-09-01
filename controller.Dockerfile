FROM python:3.11-slim
WORKDIR /app
COPY requirements-controller.txt .
RUN pip install --no-cache-dir -r requirements-controller.txt
COPY fakebric fakebric
RUN useradd --create-home --uid 10001 fakebric
USER 10001
ENTRYPOINT ["python", "-m", "fakebric.controller_main"]
