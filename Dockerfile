# =====================================================================
# Train Your Brain — Dockerfile
# =====================================================================
# Base image: official Python 3.11 slim (small, includes pip).
# TensorFlow works reliably on 3.11; 3.12 also works but 3.11 is the
# most-tested combo as of 2026.
# =====================================================================
FROM python:3.13.5

# ---------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------
# PYTHONDONTWRITEBYTECODE: don't write .pyc files inside the container
# PYTHONUNBUFFERED:        flush stdout/stderr immediately (nice logs)
# TF_CPP_MIN_LOG_LEVEL:    hide TensorFlow's noisy C++ warnings
# =====================================================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_CPP_MIN_LOG_LEVEL=2

# ---------------------------------------------------------------------
# Working directory inside the container
# ---------------------------------------------------------------------
# All relative paths in config.py (e.g. "data/data_banknote_authentication.txt")
# resolve relative to this directory.
# =====================================================================
WORKDIR /app

# ---------------------------------------------------------------------
# System packages
# ---------------------------------------------------------------------
# build-essential: some Python packages compile C extensions at install
# curl:           useful for health-checking from inside the container
# =====================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------------
# Copy requirements first — this lets Docker reuse the pip-install layer
# when only your app code changes (huge speedup on rebuild).
# =====================================================================
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Gunicorn is a production-grade WSGI server. We install it here
# rather than in requirements.txt because it's Docker-specific.
RUN pip install --no-cache-dir gunicorn==22.0.0

# ---------------------------------------------------------------------
# Application code
# ---------------------------------------------------------------------
# Copy only what run.py needs: config, run, the app package, the data.
# =====================================================================
COPY config.py run.py ./
COPY app/ ./app/
COPY data/ ./data/

# ---------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------
# The container listens on 5000. EXPOSE is documentation + the port
# that `-P` publishes; the real binding is done by `docker run -p`.
# =====================================================================
EXPOSE 5000

# ---------------------------------------------------------------------
# Start command
# ---------------------------------------------------------------------
# Gunicorn imports `run:app` (the Flask app object from run.py).
#   --workers 1     : TensorFlow is RAM-hungry; 1 worker avoids OOM
#   --threads 4     : let 4 requests train in parallel (mostly web I/O)
#   --timeout 300   : training can take minutes; default is 30s (too short)
#   --bind 0.0.0.0  : REQUIRED inside Docker (127.0.0.1 is unreachable)
# =====================================================================
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "300", "run:app"]