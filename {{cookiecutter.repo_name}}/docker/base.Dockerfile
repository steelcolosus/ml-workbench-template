# syntax=docker/dockerfile:1
#
# Stages shared by every image (built through docker-bake.hcl):
#   runtime: Python, the project folder /app and its .venv on PATH
#   builder: runtime + uv, to install the locked dependencies into /app/.venv

ARG PYTHON_VERSION={{cookiecutter.python_version}}
ARG UV_VERSION=0.6.6

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PROJECT_ROOT=/app \
    PATH="/app/.venv/bin:$PATH" \
    GIT_PYTHON_REFRESH=quiet
WORKDIR /app

FROM runtime AS builder
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_FROZEN=1
