import json

import pandas as pd
import pytest

from core.store import DataEngine, RemoteStorage, Store


class MemoryStorage(RemoteStorage):
    """In-memory backend: implements only the RemoteStorage primitives."""

    scheme = "mem"

    def __init__(self):
        self.objects = {}

    def exists(self, bucket, key):
        return (bucket, key) in self.objects

    def list_keys(self, bucket, prefix):
        return sorted(
            k for b, k in self.objects if b == bucket and k.startswith(prefix)
        )

    def get_file(self, bucket, key, local):
        local.write_bytes(self.objects[(bucket, key)])

    def put_file(self, local, bucket, key):
        self.objects[(bucket, key)] = local.read_bytes()

    def delete_keys(self, bucket, keys):
        for key in keys:
            del self.objects[(bucket, key)]


class RecordsEngine(DataEngine):
    """Engine for lists of dicts, stored as JSON."""

    def owns(self, df):
        return isinstance(df, list)

    def read(self, path, fmt, columns=None, dtypes=None, parse_dates=None, **options):
        with open(path) as fp:
            records = json.load(fp)
        if columns:
            records = [{k: r[k] for k in columns} for r in records]
        return records

    def write(self, df, path, fmt, **options):
        with open(path, "w") as fp:
            json.dump(df, fp)


def make_store(tmp_path, **kwargs):
    return Store(
        local_root=tmp_path / "data",
        locations=dict(raw=dict(path="raw"), models=None),
        bucket="bucket",
        **kwargs,
    )


def test_custom_remote_backend(tmp_path):
    remote = MemoryStorage()
    store = make_store(tmp_path, sync_s3=True, remote=remote)

    path = store.save_data("raw", "x.csv", pd.DataFrame(dict(a=[1, 2])))
    assert sorted(k for _, k in remote.objects) == ["raw/x.csv"]
    assert store.uri("raw", "x.csv") == "mem://bucket/raw/x.csv"

    path.unlink()
    assert store.load_data("raw", "x.csv")["a"].tolist() == [1, 2]


def test_custom_remote_mirrors_folders(tmp_path):
    remote = MemoryStorage()
    store = make_store(tmp_path, sync_s3=True, remote=remote)

    def writer(files):
        def write(path):
            path.mkdir()
            for file in files:
                (path / file).write_text(file)

        return write

    store.save_artifact("models", "m", writer=writer(["a", "b"]))
    store.save_artifact("models", "m", writer=writer(["a"]))

    assert sorted(k for _, k in remote.objects) == ["models/m/a"]


def test_custom_engine(tmp_path):
    store = make_store(tmp_path, engines=dict(records=RecordsEngine()))

    store.save_data("raw", "r.json", [dict(a=1, b=2)])

    assert store.load_data("raw", "r.json", engine="records", columns=["a"]) == [
        dict(a=1)
    ]
    assert store.load_data("raw", "r.json")["b"].tolist() == [2]


def test_unknown_engine_lists_the_available_ones(tmp_path):
    with pytest.raises(ValueError, match="dask"):
        make_store(tmp_path).load_data("raw", "x.csv", engine="polars")


def test_saving_an_unsupported_type_is_an_error(tmp_path):
    with pytest.raises(TypeError, match="No engine"):
        make_store(tmp_path).save_data("raw", "x.json", {"a": 1})
