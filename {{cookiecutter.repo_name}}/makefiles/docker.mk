# The project's images (docker/*.Dockerfile), built with bake from
# docker/docker-bake.hcl: building, linting, pushing and running them through
# docker-compose.yml

.PHONY: image images push ecr-login lint-docker docker-pipeline docker-serve

BAKE_CMD := docker buildx bake -f docker/docker-bake.hcl
BAKE := $(BAKE_CMD) --load
HADOLINT := docker run --rm -i hadolint/hadolint:v2.14.0

# The images need uv.lock: created by `make venv`, or here when it's missing
uv.lock: pyproject.toml
	$(UV) lock

# make image TARGET=serving
image: uv.lock ##@Docker Build one image: TARGET=pipeline (default), serving or mlflow
	$(BAKE) $(or $(TARGET),pipeline)

images: uv.lock ##@Docker Build every image (in parallel)
	$(BAKE)

# make push REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com/ [TARGET=serving]
push: uv.lock ##@Docker Build and push images to REGISTRY (every image, or TARGET=...)
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY (in .env or REGISTRY=...), ending in /" && exit 1)
	$(BAKE_CMD) --push $(TARGET)

# Logs Docker in to the ECR registry in REGISTRY with the AWS CLI
ecr-login: ##@Docker Log Docker in to the ECR registry in REGISTRY (AWS_REGION, AWS_PROFILE)
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY (in .env or REGISTRY=...)" && exit 1)
	aws ecr get-login-password --region $(AWS_REGION) $(if $(AWS_PROFILE),--profile $(AWS_PROFILE)) \
		| docker login --username AWS --password-stdin $(firstword $(subst /, ,$(REGISTRY)))

lint-docker: ##@Docker Lint the Dockerfiles with hadolint
	@for f in docker/*.Dockerfile; do echo "hadolint $$f"; $(HADOLINT) < $$f || exit 1; done

# make docker-pipeline STEPS=basic_cleaning ARGS="store.sync_s3=true"
docker-pipeline: uv.lock ##@Docker Build and run the pipeline image (STEPS and ARGS as in `make pipeline`)
	$(BAKE) pipeline mlflow
	docker compose --profile pipeline run --rm pipeline \
		"main.steps='$(or $(STEPS),all)'" $(ARGS)

docker-serve: uv.lock ##@Docker Build and run the serving image on SERVING_PORT (SERVING_MODEL_NAME=...)
	$(BAKE) serving
	docker compose --profile serving up serving
