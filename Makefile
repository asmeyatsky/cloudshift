.PHONY: dev build test lint clean

dev:
	maturin develop --release

build:
	maturin build --release

test: test-rust test-python

test-rust:
	cargo test --workspace

test-python:
	pytest tests/ -v

lint:
	cargo clippy --workspace -- -D warnings
	ruff check python/ tests/
	ruff format --check python/ tests/

format:
	ruff format python/ tests/

clean:
	cargo clean
	rm -rf dist/ build/ *.egg-info __pycache__

ui-dev:
	cd ui && npm run dev

ui-build:
	cd ui && npm run build

vscode-build:
	cd vscode-extension && npm run compile
