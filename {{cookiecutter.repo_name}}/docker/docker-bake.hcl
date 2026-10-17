# Build plan for the project's images (docs: https://docs.docker.com/build/bake/).
#
#   docker buildx bake -f docker/docker-bake.hcl            every image
#   docker buildx bake -f docker/docker-bake.hcl serving    one image
#
# `make image TARGET=...`, `make images` and `make push` run these. Every
# variable can be overridden with an environment variable of the same name; the
# Makefile passes the project's Python and uv versions, version, git commit and
# source URL, and REGISTRY from .env.

variable "PYTHON_VERSION" {
  default = "{{cookiecutter.python_version}}"
}

# The Python base image; pin a digest with
# PYTHON_IMAGE=python:3.13-slim@sha256:<digest>
variable "PYTHON_IMAGE" {
  default = "python:${PYTHON_VERSION}-slim"
}

variable "UV_VERSION" {
  default = "0.13.1"
}

variable "IMAGE_NAME" {
  default = "{{cookiecutter.repo_name}}"
}

# Registry prefix for `make push`, ending in "/", e.g.
# 123456789012.dkr.ecr.us-east-1.amazonaws.com/ (empty: local images)
variable "REGISTRY" {
  default = ""
}

# For the image labels (the Makefile reads them from pyproject.toml and git)
variable "PROJECT_VERSION" {
  default = "0.0.0"
}

variable "GIT_SHA" {
  default = ""
}

variable "SOURCE_URL" {
  default = ""
}

# Built by `docker buildx bake` without a target
group "default" {
  targets = ["pipeline", "serving", "mlflow"]
}

# Settings shared by every target
target "_common" {
  args = {
    PYTHON_VERSION = PYTHON_VERSION
    PYTHON_IMAGE   = PYTHON_IMAGE
    UV_VERSION     = UV_VERSION
  }
}

# Shared stages from base.Dockerfile. They aren't images of their own: the
# images use them as `FROM runtime` and `FROM builder` (see `contexts` below).
target "runtime" {
  inherits   = ["_common"]
  context    = "docker"
  dockerfile = "base.Dockerfile"
  target     = "runtime"
}

target "builder" {
  inherits   = ["_common"]
  context    = "docker"
  dockerfile = "base.Dockerfile"
  target     = "builder"
}

# The images. Their build context is the project root; each Dockerfile has its
# own <name>.Dockerfile.dockerignore listing the files it gets. They carry the
# standard OCI labels (version, git commit, source).
target "_image" {
  inherits = ["_common"]
  context  = "."
  contexts = {
    runtime = "target:runtime"
    builder = "target:builder"
  }
  labels = {
    "org.opencontainers.image.version"  = PROJECT_VERSION
    "org.opencontainers.image.revision" = GIT_SHA
    "org.opencontainers.image.source"   = SOURCE_URL
  }
}

# Each image is tagged <name>:<image> and <name>:<image>-<version>
target "pipeline" {
  inherits   = ["_image"]
  dockerfile = "docker/pipeline.Dockerfile"
  tags = [
    "${REGISTRY}${IMAGE_NAME}:pipeline",
    "${REGISTRY}${IMAGE_NAME}:pipeline-${PROJECT_VERSION}",
  ]
  labels = {
    "org.opencontainers.image.title"       = "${IMAGE_NAME}-pipeline"
    "org.opencontainers.image.description" = "Runs the pipeline (main.py)"
  }
}

target "serving" {
  inherits   = ["_image"]
  dockerfile = "docker/serving.Dockerfile"
  tags = [
    "${REGISTRY}${IMAGE_NAME}:serving",
    "${REGISTRY}${IMAGE_NAME}:serving-${PROJECT_VERSION}",
  ]
  labels = {
    "org.opencontainers.image.title"       = "${IMAGE_NAME}-serving"
    "org.opencontainers.image.description" = "Serves the project's models (FastAPI)"
  }
}

# The MLflow tracking server run by docker-compose.yml
target "mlflow" {
  inherits   = ["_image"]
  dockerfile = "docker/mlflow.Dockerfile"
  tags = [
    "${REGISTRY}${IMAGE_NAME}:mlflow",
    "${REGISTRY}${IMAGE_NAME}:mlflow-${PROJECT_VERSION}",
  ]
  labels = {
    "org.opencontainers.image.title"       = "${IMAGE_NAME}-mlflow"
    "org.opencontainers.image.description" = "MLflow tracking server"
  }
}
