#!/bin/bash
set -e
pnpm install --frozen-lockfile
# Python/SQLAlchemy owns the business schema; never push the empty Drizzle template.
UV_PROJECT_ENVIRONMENT=.pythonlibs uv sync --frozen
