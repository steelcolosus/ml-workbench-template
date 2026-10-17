# syntax=docker/dockerfile:1
#
# MLflow tracking server image: the tracking-server extra (full mlflow and
# psycopg) at the versions in uv.lock, so the server matches the clients.
# docker-compose.yml runs it with the PostgreSQL backend; build it with
# `make image TARGET=mlflow` (docker-bake.hcl provides `builder` and `runtime`).

FROM builder AS build
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project --no-default-groups --extra tracking-server

FROM runtime
COPY --from=build /app/.venv /app/.venv
EXPOSE 5000
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]
# The command (backend store, artifacts, allowed hosts) is set in docker-compose.yml
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
