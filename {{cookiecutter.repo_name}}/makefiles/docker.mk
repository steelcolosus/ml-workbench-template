# The project's images (docker/Dockerfile) and running them through docker-compose.yml

.PHONY: image docker-pipeline docker-serve docker-test

# The images need uv.lock: created by `make venv`, or here when it's missing
uv.lock: pyproject.toml
	$(UV) lock

# make image TARGET=serving
image: uv.lock ##@Docker Build an image: TARGET=pipeline (default), serving or test
	docker build -f docker/Dockerfile --target $(or $(TARGET),pipeline) \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) --build-arg UV_VERSION=$(UV_VERSION) \
		-t $(IMAGE_NAME):$(or $(TARGET),pipeline) .

# make docker-pipeline STEPS=basic_cleaning ARGS="store.sync_s3=true"
docker-pipeline: uv.lock ##@Docker Run the pipeline in its image (STEPS and ARGS as in `make pipeline`)
	docker compose --profile pipeline run --rm --build pipeline \
		"main.steps='$(or $(STEPS),all)'" $(ARGS)

docker-serve: uv.lock ##@Docker Run the API in its image on SERVING_PORT (SERVING_MODEL_NAME=...)
	docker compose --profile serving up --build serving

docker-test: uv.lock ##@Docker Run the tests in the test image
	docker compose --profile test run --rm --build test
