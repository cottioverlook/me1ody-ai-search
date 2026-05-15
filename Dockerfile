# Hugging Face Spaces Docker entrypoint for the backend service.
FROM python:3.12-slim

RUN useradd -m -u 1000 user

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    APP_ENV=huggingface \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite+aiosqlite:////tmp/me1ody.db \
    EMBEDDING_BACKEND=hash \
    DEMO_MODE=false \
    PORT=7860

WORKDIR /home/user/app

COPY --chown=user backend/requirements.docker.txt ./requirements.txt
COPY --chown=user backend/pyproject.toml ./
COPY --chown=user backend/app ./app

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

USER user

EXPOSE 7860

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
