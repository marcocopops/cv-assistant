FROM python:3.13-slim

# Container-friendly Python: no .pyc files, unbuffered logs, no pip cache.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first: this layer is only rebuilt when requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Unprivileged user: a compromised process gets no root access in the container.
RUN useradd --system --uid 10001 --no-create-home app

# Application code last, since it changes most often.
# Files stay owned by root, so the app user can read but not modify them.
COPY app/ app/

USER app
EXPOSE 8000

# Single process on purpose: the inference queue lives in memory and must be unique.
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
