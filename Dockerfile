FROM python:3.12-slim

WORKDIR /app
COPY display_inspector/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY display_inspector /app/display_inspector
ENV PYTHONPATH=/app
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "display_inspector"]
