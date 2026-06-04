FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY . .

RUN uv sync --frozen

EXPOSE 2552

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "2552"]