FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app

# Najpierw same zależności — warstwa cache'owana, dopóki nie zmieni się lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 kupto
USER kupto

EXPOSE 8000
# Strumienie SSE (lista na żywo) nie kończą się same, więc przy zatrzymaniu uvicorn czeka na nie
# najwyżej 8 s — przed SIGKILL Dockera po 10 s — i domyka aplikację (zamknięcie LISTEN).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn --factory kupto.main:create_app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 8"]
