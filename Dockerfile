# ─────────────── 階段 1：只裝依賴（最容易被快取） ───────────────
FROM ghcr.io/astral-sh/uv:python3.11-alpine AS deps

WORKDIR /app

# 先只複製會影響依賴的兩個檔案（這兩個檔案變動最少）
COPY pyproject.toml uv.lock* ./

# 關鍵優化旗標
ENV UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 只裝依賴，不裝專案本身 → 這層最容易被 Docker 快取
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# ─────────────── 階段 2：最終映像（程式碼變動才重新執行） ───────────────
FROM ghcr.io/astral-sh/uv:python3.11-alpine

WORKDIR /app

# 把前面裝好的 .venv 整個複製過來（最快）
COPY --from=deps /app/.venv /app/.venv

# 這時候才複製全部程式碼（改動最頻繁）
COPY . .

# 可選：如果你的 CMD 要直接用 python 而非 uv run，可以把 venv 加到 PATH
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]
# 或是維持原樣
# CMD ["uv", "run", "main.py"]