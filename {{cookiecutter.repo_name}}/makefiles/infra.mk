# Services in docker-compose.yml (PostgreSQL, the local S3 server) and AWS login

.PHONY: docker-compose down login

DOWN_OPTS = --remove-orphans

# run docker compose
docker-compose: ##@Infra Run docker compose
	docker compose up -d --wait

down: ##@Infra Stop and remove containers, networks, images, and volumes
	docker compose down ${DOWN_OPTS}

login: ##@Infra Login to AWS SSO
	aws sso login --profile ${AWS_PROFILE}
