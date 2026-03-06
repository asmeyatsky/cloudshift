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

COPY --from=python-builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

COPY --from=ui-builder /build/ui/dist/ /app/static/
COPY patterns/ /app/patterns/

ENV CLOUDSHIFT_PATTERNS_DIR=/app/patterns
ENV CLOUDSHIFT_STATIC_DIR=/app/static

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "cloudshift.presentation.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
