FROM python:3.14-slim

WORKDIR /app

# Install Poetry package manager
RUN pip install --no-cache-dir "poetry>=2.0.0,<3.0.0"

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml poetry.lock ./

# Install dependencies:
# - Disable virtualenv creation (install into system Python)
# - Install only main dependencies (skip dev group)
# - Skip installing the current project as a package
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction

# Copy application source code
COPY main.py .

# Expose the port the app listens on
EXPOSE 8000

# Start the FastAPI app with Uvicorn ASGI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
