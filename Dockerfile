FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

RUN pip install --no-cache-dir -e . && \
    python -c "import task_scaffolder; print('task_scaffolder', task_scaffolder.__version__)"

CMD ["python", "-m", "task_scaffolder.cli", "scaffold", "--snapshot-dir", "tests/fixtures/github_snapshots", "--out", "/app/bundles"]
