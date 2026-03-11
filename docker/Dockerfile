# Build for linux/amd64 so the same image runs on Cloud Run (x86) and ARM (e.g. Mac).
FROM --platform=linux/amd64 rust:1.93 AS rust-builder
WORKDIR /build
COPY Cargo.toml Cargo.lock* ./
COPY rust/ rust/
RUN cargo build --release --manifest-path rust/cloudshift-core/Cargo.toml

# Maturin needs Rust to build the wheel; use this stage (has cargo) to produce it.
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages maturin
COPY pyproject.toml .
COPY python/ python/
RUN maturin build --release --out dist

FROM --platform=linux/amd64 python:3.13-slim AS python-builder
WORKDIR /build
COPY --from=rust-builder /build/dist/ ./dist/

FROM --platform=linux/amd64 node:22-slim AS ui-builder
WORKDIR /build/ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install
COPY ui/ .
RUN npm run build

FROM --platform=linux/amd64 python:3.13-slim
WORKDIR /app

# Git required for POST /api/projects/from-git (clone repo for scan/plan/apply).
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user
RUN groupadd -g 10001 cloudshift && \
    useradd -u 10001 -g cloudshift -m -s /sbin/nologin cloudshift

COPY --from=python-builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

COPY --from=ui-builder --chown=cloudshift:cloudshift /build/ui/dist/ /app/static/
COPY --chown=cloudshift:cloudshift patterns/ /app/patterns/

# Create data directory and set permissions
RUN mkdir -p /app/data && chown cloudshift:cloudshift /app/data

ENV CLOUDSHIFT_PATTERNS_DIR=/app/patterns
ENV CLOUDSHIFT_STATIC_DIR=/app/static
ENV CLOUDSHIFT_DATA_DIR=/app/data
ENV CLOUDSHIFT_DB_PATH=/app/data/cloudshift.db

USER cloudshift

EXPOSE 8000

# Use PORT so the same image works on Cloud Run (sets PORT=8080) and elsewhere (default 8000).
ENV PORT=8000
CMD ["sh", "-c", "exec python -m uvicorn cloudshift.presentation.api.app:create_app --factory --host 0.0.0.0 --port ${PORT}"]
