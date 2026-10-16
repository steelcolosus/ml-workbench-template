# The MLflow tracking server and its local stores

.PHONY: mlflow-server mlflow-kill

# run mlflow server
mlflow-server: ##@MLflow Run mlflow server
	$(MLFLOW) server \
		--backend-store-uri postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${MLFLOW_BACKEND_STORE}:${POSTGRES_PORT}/${POSTGRES_DB} \
		--artifacts-destination ${MLFLOW_ARTIFACT_STORE} \
		--host ${MLFLOW_TRACKING_SERVER_HOST} \
		--port ${MLFLOW_TRACKING_SERVER_PORT} \
		$(if $(MLFLOW_ALLOWED_HOSTS),--allowed-hosts "$(MLFLOW_ALLOWED_HOSTS)")

mlflow-kill: ##@MLflow Kill mlflow server
	-@lsof -t -i:${MLFLOW_TRACKING_SERVER_PORT} | xargs kill -9 2>/dev/null || true

# Folders of the artifact store and the PostgreSQL data (created by `make setup`)
${MLFLOW_ARTIFACT_STORE}:
	mkdir -p ${MLFLOW_ARTIFACT_STORE}

${POSTGRES_VOLUME}:
	mkdir -p ${POSTGRES_VOLUME}
