FROM python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce
WORKDIR /app
COPY materials/app.py /app/
COPY materials/templates /app/templates
COPY materials/static /app/static
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock
EXPOSE 5000
CMD ["python", "app.py"]
