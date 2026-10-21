FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY app app
RUN pip install --no-cache-dir --no-deps . && useradd --create-home servicepulse
COPY alembic.ini .
COPY migrations migrations
COPY tests tests
USER servicepulse
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
