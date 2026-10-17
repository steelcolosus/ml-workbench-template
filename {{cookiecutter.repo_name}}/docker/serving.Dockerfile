# syntax=docker/dockerfile:1
#
# Serving image: base dependencies + the serving extra, running the API.
# Build it with `make image TARGET=serving` (docker-bake.hcl provides the
# `builder` and `runtime` stages from base.Dockerfile).

# `builder` and `runtime` are stages bake passes in (see docker-bake.hcl), not
# registry images, so hadolint's "tag the image version" rule doesn't apply.
# hadolint ignore=DL3006
FROM builder AS build
WORKDIR /app
# Dependencies first: this layer is reused until pyproject.toml or uv.lock change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project --no-default-groups --extra serving
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-default-groups --extra serving

# hadolint ignore=DL3006
FROM runtime
COPY --from=build /app /app
# The API doesn't need root; it can still download models into /app/models
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/models \
    && chown -R app /app/data /app/models
USER 1000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
