# Services in docker-compose.yml (PostgreSQL, the MLflow server, the local S3 server) and AWS login

.PHONY: docker-compose down login

DOWN_OPTS = --remove-orphans

# Builds the mlflow image, then starts PostgreSQL and the MLflow server
docker-compose: uv.lock ##@Infra Start the docker-compose services (PostgreSQL, MLflow)
	$(BAKE) mlflow
	docker compose up -d --wait

down: ##@Infra Stop and remove containers, networks, images, and volumes
	docker compose down ${DOWN_OPTS}

login: ##@Infra Login to AWS SSO
	aws sso login --profile ${AWS_PROFILE}
