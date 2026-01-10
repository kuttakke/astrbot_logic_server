FROM ghcr.io/astral-sh/uv:python3.11-alpine
WORKDIR /app
COPY . /app
ENV UV_NO_DEV=1
RUN uv sync --locked

CMD ["uv", "run", "main.py"]