#!/usr/bin/env bash
set -euo pipefail
uv sync --locked
uv run --locked ruff check currency scripts tests
uv run --locked ruff format --check currency scripts tests
mkdir -p reports
uv run --locked pytest --junitxml=reports/junit.xml
