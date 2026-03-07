FROM rust:1.93 AS rust-builder
WORKDIR /build
COPY Cargo.toml Cargo.lock* ./
COPY rust/ rust/
RUN cargo build --release --manifest-path rust/cloudshift-core/Cargo.toml

FROM python:3.13-slim AS python-builder
RUN pip install maturin
WORKDIR /build
COPY --from=rust-builder /build/ .
COPY pyproject.toml .
COPY python/ python/
RUN maturin build --release --out dist

FROM node:22-slim AS ui-builder
WORKDIR /build/ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm ci
COPY ui/ .
RUN npm run build

FROM python:3.13-slim
WORKDIR /app

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

CMD ["python", "-m", "uvicorn", "cloudshift.presentation.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
