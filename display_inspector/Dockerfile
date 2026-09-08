FROM python:3.12-slim
WORKDIR /app
COPY display_inspector /app/display_inspector
COPY display_inspector/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
EXPOSE 8080
ENV PORT=8080
CMD ["python", "-m", "display_inspector"]
