import pandas as pd
import pytest
from fastapi.testclient import TestClient

from core.model import CustomModel
from core.store import Store
from serving.app import create_app
from serving.settings import Settings


class Doubler(CustomModel):
    def predict(self, context, model_input, params=None):
        return model_input * 2


@pytest.fixture
def store(tmp_path):
    store = Store(local_root=tmp_path / "data", locations=dict(models=None))
    sample = pd.DataFrame(dict(x=[1.0, 2.0]))
    Doubler().save(store, "doubler", sample=sample, log_model=False)
    return store


@pytest.fixture
def client(store):
    app = create_app(Settings(model_name="doubler"), store)
    with TestClient(app) as client:  # runs the startup that loads the model
        yield client


@pytest.fixture
def client_without_model(store):
    with TestClient(create_app(Settings(), store)) as client:
        yield client


def test_health(client):
    assert client.get("/health").json() == dict(status="ok")


def test_ready_with_a_model(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["model_name"] == "doubler"


def test_predict(client):
    response = client.post("/predict", json=dict(records=[dict(x=1.5), dict(x=4.0)]))

    assert response.status_code == 200
    assert response.json() == dict(
        model_name="doubler", predictions=[dict(x=3.0), dict(x=8.0)]
    )


def test_whole_numbers_are_accepted_for_float_columns(client):
    response = client.post("/predict", json=dict(records=[dict(x=2)]))

    assert response.status_code == 200
    assert response.json()["predictions"] == [dict(x=4.0)]


def test_model_info_shows_the_signature(client):
    info = client.get("/model").json()

    assert info["name"] == "doubler"
    assert info["inputs"] == [dict(type="double", name="x", required=True)]


def test_records_that_dont_match_the_signature_are_rejected(client):
    response = client.post("/predict", json=dict(records=[dict(y=1.0)]))

    assert response.status_code == 422
    assert "x" in response.json()["detail"]


def test_empty_records_are_rejected(client):
    assert client.post("/predict", json=dict(records=[])).status_code == 422


def test_without_a_model_it_starts_but_isnt_ready(client_without_model):
    assert client_without_model.get("/health").status_code == 200
    assert client_without_model.get("/ready").status_code == 503
    response = client_without_model.post("/predict", json=dict(records=[dict(x=1)]))
    assert response.status_code == 503


def test_a_missing_model_fails_startup(store):
    app = create_app(Settings(model_name="missing"), store)

    with pytest.raises(FileNotFoundError), TestClient(app):
        pass


def test_docs_describe_the_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert {"/health", "/ready", "/model", "/predict"} <= set(paths)
    assert client.get("/docs").status_code == 200
