# syntax=docker/dockerfile:1
#
# Pipeline image: base dependencies + the pipeline extra, running main.py.
# Build it with `make image TARGET=pipeline` (docker-bake.hcl provides the
# `builder` and `runtime` stages from base.Dockerfile).

FROM builder AS build
# Dependencies first: this layer is reused until pyproject.toml or uv.lock change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project --no-default-groups --extra pipeline
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-default-groups --extra pipeline

FROM runtime
COPY --from=build /app /app
# Steps run in this image's environment. Arguments are Hydra overrides, e.g.
# `docker run <image> main.steps=basic_cleaning store.sync_s3=true`
ENTRYPOINT ["python", "main.py", "launcher.env_manager=local"]
