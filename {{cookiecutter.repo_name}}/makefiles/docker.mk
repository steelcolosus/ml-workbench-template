# The project's images (docker/*.Dockerfile), built with bake from
# docker/docker-bake.hcl, and running them through docker-compose.yml

.PHONY: image images docker-pipeline docker-serve

BAKE := docker buildx bake --load -f docker/docker-bake.hcl

# The images need uv.lock: created by `make venv`, or here when it's missing
uv.lock: pyproject.toml
	$(UV) lock

# make image TARGET=serving
image: uv.lock ##@Docker Build one image: TARGET=pipeline (default) or serving
	$(BAKE) $(or $(TARGET),pipeline)

images: uv.lock ##@Docker Build every image (in parallel)
	$(BAKE)

# make docker-pipeline STEPS=basic_cleaning ARGS="store.sync_s3=true"
docker-pipeline: uv.lock ##@Docker Build and run the pipeline image (STEPS and ARGS as in `make pipeline`)
	$(BAKE) pipeline
	docker compose --profile pipeline run --rm pipeline \
		"main.steps='$(or $(STEPS),all)'" $(ARGS)

docker-serve: uv.lock ##@Docker Build and run the serving image on SERVING_PORT (SERVING_MODEL_NAME=...)
	$(BAKE) serving
	docker compose --profile serving up serving
