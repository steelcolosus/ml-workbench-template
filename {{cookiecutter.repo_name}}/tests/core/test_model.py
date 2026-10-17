import mlflow
import pandas as pd
import pytest

from core.model import CustomModel
from core.store import RemoteStorage, Store


class Doubler(CustomModel):
    def predict(self, context, model_input, params=None):
        return model_input * 2


@pytest.fixture
def store(tmp_path):
    return Store(
        local_root=tmp_path / "data",
        locations=dict(models=dict(path=str(tmp_path / "models"))),
    )


@pytest.fixture
def tracking(tmp_path):
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    yield
    mlflow.set_tracking_uri(previous)


def test_save_and_load_through_the_store(store):
    sample = pd.DataFrame(dict(x=[1.0, 2.0]))

    info = Doubler().save(store, "doubler", sample=sample, log_model=False)

    assert info is None
    assert store.path("models", "doubler").is_dir()
    loaded = CustomModel.load(store, "doubler")
    assert loaded.predict(pd.DataFrame(dict(x=[3.0])))["x"].tolist() == [6.0]


def test_save_logs_the_model_to_the_active_run(store, tracking):
    sample = pd.DataFrame(dict(x=[1.0]))

    with mlflow.start_run():
        info = Doubler().save(store, "doubler", sample=sample)

    logged = mlflow.pyfunc.load_model(info.model_uri)
    assert logged.predict(pd.DataFrame(dict(x=[4.0])))["x"].tolist() == [8.0]


class RecordingStorage(RemoteStorage):
    """Remote that only records uploaded keys."""

    def __init__(self):
        self.uploaded = []

    def exists(self, bucket, key):
        return False

    def list_keys(self, bucket, prefix):
        return []

    def get_file(self, bucket, key, local):
        raise FileNotFoundError(key)

    def put_file(self, local, bucket, key):
        self.uploaded.append(key)

    def delete_keys(self, bucket, keys):
        pass


def test_save_keeps_the_model_local_unless_sync_is_true(tmp_path):
    remote = RecordingStorage()
    store = Store(
        local_root=tmp_path / "data",
        locations=dict(models=None),
        sync_s3=True,
        bucket="bucket",
        remote=remote,
    )
    sample = pd.DataFrame(dict(x=[1.0]))

    Doubler().save(store, "local_only", sample=sample, log_model=False)
    assert remote.uploaded == []

    Doubler().save(store, "uploaded", sample=sample, log_model=False, sync=True)
    assert remote.uploaded and all(
        k.startswith("models/uploaded/") for k in remote.uploaded
    )
