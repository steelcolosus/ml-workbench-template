# Build plan for the project's images (docs: https://docs.docker.com/build/bake/).
#
#   docker buildx bake -f docker/docker-bake.hcl            every image
#   docker buildx bake -f docker/docker-bake.hcl serving    one image
#
# `make image TARGET=...` and `make images` run these. Variables can be
# overridden with environment variables of the same name; the Makefile passes
# the project's Python and uv versions.

variable "PYTHON_VERSION" {
  default = "{{cookiecutter.python_version}}"
}

variable "UV_VERSION" {
  default = "0.13.1"
}

variable "IMAGE_NAME" {
  default = "{{cookiecutter.repo_name}}"
}

# Built by `docker buildx bake` without a target
group "default" {
  targets = ["pipeline", "serving", "mlflow"]
}

# Settings shared by every target
target "_common" {
  args = {
    PYTHON_VERSION = PYTHON_VERSION
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
# own <name>.Dockerfile.dockerignore listing the files it gets.
target "_image" {
  inherits = ["_common"]
  context  = "."
  contexts = {
    runtime = "target:runtime"
    builder = "target:builder"
  }
}

target "pipeline" {
  inherits   = ["_image"]
  dockerfile = "docker/pipeline.Dockerfile"
  tags       = ["${IMAGE_NAME}:pipeline"]
}

target "serving" {
  inherits   = ["_image"]
  dockerfile = "docker/serving.Dockerfile"
  tags       = ["${IMAGE_NAME}:serving"]
}

# The MLflow tracking server run by docker-compose.yml
target "mlflow" {
  inherits   = ["_image"]
  dockerfile = "docker/mlflow.Dockerfile"
  tags       = ["${IMAGE_NAME}:mlflow"]
}
