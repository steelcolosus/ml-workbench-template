# syntax=docker/dockerfile:1
#
# One image per target, each with only the dependency set it needs
# (see README > Docker):
#
#   docker build --target pipeline .   base + pipeline extra; runs main.py
#   docker build --target serving .    base + serving extra; runs the API
#   docker build --target test .       base + every extra + test group; runs pytest
#
# --target picks the image: Docker builds that stage and only the stages it
# copies from, so each image installs its own set. `make image TARGET=...`
# passes the project's Python and uv versions. Needs uv.lock (`make venv`).

ARG PYTHON_VERSION={{cookiecutter.python_version}}
ARG UV_VERSION=0.6.6

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# Base of every image: Python, the project in /app and its venv on PATH
FROM python:${PYTHON_VERSION}-slim AS python
ENV PYTHONUNBUFFERED=1 \
    PROJECT_ROOT=/app \
    PATH="/app/.venv/bin:$PATH" \
    GIT_PYTHON_REFRESH=quiet
WORKDIR /app

# Builder base: uv installs the exact versions in uv.lock into /app/.venv
FROM python AS builder
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_FROZEN=1

# Each *-deps stage installs the dependencies first (cached until pyproject.toml
# or uv.lock change), then the project's code.

FROM builder AS pipeline-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project --no-default-groups --extra pipeline
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-default-groups --extra pipeline

FROM builder AS serving-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project --no-default-groups --extra serving
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-default-groups --extra serving

FROM builder AS test-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project --no-default-groups --all-extras --group test
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-default-groups --all-extras --group test

# Final images: the venv and the code, without uv or its cache

FROM python AS test
COPY --from=test-deps /app /app
CMD ["pytest"]

FROM python AS serving
COPY --from=serving-deps /app /app
# The API doesn't need root; it can still download models into /app/models
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/models \
    && chown -R app /app/data /app/models
USER app
EXPOSE 8000
CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Last, so it's also what `docker build .` builds without --target.
# Steps run in the image's environment; arguments are Hydra overrides, e.g.
# `docker run <image> main.steps=basic_cleaning store.sync_s3=true`
FROM python AS pipeline
COPY --from=pipeline-deps /app /app
ENTRYPOINT ["python", "main.py", "launcher.env_manager=local"]
