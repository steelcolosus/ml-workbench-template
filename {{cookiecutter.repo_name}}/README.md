#{{cookiecutter.project_name}}

{{cookiecutter.description}}

This is a Makefile-based project designed to set up a development environment for running MLflow server and Jupyter Notebook in parallel. It creates a virtual environment, installs required dependencies, sets up a Docker Compose environment, and manages storage for artifacts and PostgreSQL.

##Requirements

-   Python 3
-   Docker
-   Docker Compose

##Getting Started

1. Clone the repository.
2. Make sure Docker and Docker Compose are installed.
3. Run make to set up the environment and run the default targets.

##Targets

-   `venv`: Create a virtual environment and install requirements.
-   `docker-compose`: Run Docker Compose to set up the required services.
-   `mlflow-server`: Run the MLflow server with a PostgreSQL backend and artifact store.
-   `jupyter-notebook`: Run Jupyter Notebook in the virtual environment.
-   `setup`: Set up the environment and storage for MLflow and PostgreSQL.
-   `run`: Run mlflow-server and jupyter-notebook targets in parallel (default target).
-   `clean`: Clean up Docker resources.
-   `clean`-all: Clean up all resources, including Python and storage.
-   `down`: Stop and remove containers, networks, images, and volumes.
-   `prune`: Prune unused Docker resources.

##Usage
Run the default target to set up the environment and run MLflow server and Jupyter Notebook:

```shell
make
```

Run individual targets as needed:

```shell
make <target-name>
```

For example, to set up the environment without running the services:

```shell
make setup
```

To run the services in parallel after setting up the environment:

```shell
make run
```

To clean up all resources:

```shell
make clean-all
```

To only clean up Docker resources:

```shell
make clean
```

Directories

-   `${MLFLOW_ARTIFACT_STORE}`: Directory for storing MLflow artifacts.
-   `${POSTGRES_VOLUME}`: Directory for storing PostgreSQL data.

##Environment Variables
The project includes a .env file containing environment variables for MLflow server, PostgreSQL, and storage directories. Modify the values as needed for your environment.

###Configuration
To configure the project, modify the values in the .env file according to your requirements. Here are the main environment variables used in the Makefile:

-   `POSTGRES_USER`: PostgreSQL user.
-   `POSTGRES_PASSWORD`: PostgreSQL password.
-   `POSTGRES_DATABASE`: PostgreSQL database name.
-   `POSTGRES_PORT`: PostgreSQL port.
-   `MLFLOW_BACKEND_STORE`: Hostname for the MLflow backend store (PostgreSQL).
-   `MLFLOW_ARTIFACT_STORE`: Directory for storing MLflow artifacts.
-   `MLFLOW_TRACKING_SERVER_HOST`: Host for the MLflow tracking server.
-   `MLFLOW_TRACKING_SERVER_PORT`: Port for the MLflow tracking server.
-   `POSTGRES_VOLUME`: Directory for storing PostgreSQL data.

###Customization
You can easily customize this project to suit your needs by adding or modifying targets in the Makefile. Here are some ideas for customization:

-   Add targets for specific data processing or training tasks.
-   Integrate additional tools, like TensorBoard or additional Jupyter Notebook extensions.
-   Add targets for deployment or packaging.

##Contributing
If you'd like to contribute to the project, feel free to submit a pull request or open an issue. We appreciate any help and feedback.
