import os
from pathlib import Path

import boto3
import pandas as pd
import pytest
from moto import mock_aws
from omegaconf import OmegaConf

from libs.store import STORE_CONFIG_ENV, Store

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
BUCKET = "ml-bucket"
ANALYTICS_BUCKET = "analytics-bucket"


def make_store(tmp_path, sync_s3=False, **overrides):
    config = dict(
        local_root=str(tmp_path / "data"),
        sync_s3=sync_s3,
        bucket=BUCKET,
        prefix="ml/project",
        locations=dict(
            raw=dict(path="raw"),
            processed=None,
            analytics=dict(
                path="analytics", bucket=ANALYTICS_BUCKET, prefix="team-x/project"
            ),
            models=dict(path=str(tmp_path / "models")),
        ),
    )
    config.update(overrides)
    return Store.from_config(config)


def sample_df():
    return pd.DataFrame(
        dict(
            id=[1, 2, 3],
            price=[10.5, 20.0, 30.25],
            city=["a", "b", "a"],
            day=["2024-01-01", "2024-01-02", "2024-01-03"],
        )
    )


def s3_keys(client, bucket):
    response = client.list_objects_v2(Bucket=bucket)
    return sorted(obj["Key"] for obj in response.get("Contents", []))


@pytest.fixture
def s3(monkeypatch):
    for var in ("AWS_PROFILE", "AWS_ENDPOINT_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        for bucket in (BUCKET, ANALYTICS_BUCKET):
            client.create_bucket(Bucket=bucket)
        yield client


# ---------------------------------------------------------------- paths


def test_path_resolves_location_folders(tmp_path):
    store = make_store(tmp_path)
    data = (tmp_path / "data").resolve()

    assert store.path("raw", "a/b.csv") == data / "raw" / "a" / "b.csv"
    assert store.path("processed") == data / "processed"
    assert store.path("models", "m") == (tmp_path / "models").resolve() / "m"


def test_uri_uses_location_bucket_and_prefix(tmp_path):
    store = make_store(tmp_path)

    assert store.uri("raw", "x.csv") == f"s3://{BUCKET}/ml/project/raw/x.csv"
    assert store.uri("analytics", "eda/r.html") == (
        f"s3://{ANALYTICS_BUCKET}/team-x/project/eda/r.html"
    )


@pytest.mark.parametrize("name", ["/etc/passwd", "../outside.csv", "a/../../b"])
def test_names_must_stay_inside_their_location(tmp_path, name):
    with pytest.raises(ValueError, match="relative"):
        make_store(tmp_path).path("raw", name)


def test_unknown_location_lists_configured_ones(tmp_path):
    with pytest.raises(ValueError, match="analytics"):
        make_store(tmp_path).path("analitycs", "x.csv")


def test_sync_without_bucket_fails_when_the_store_is_created(tmp_path):
    with pytest.raises(ValueError, match="no bucket"):
        make_store(tmp_path, sync_s3=True, bucket=None)


def test_bucket_with_a_path_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="prefix"):
        make_store(tmp_path, bucket="s3://bucket/some/path")


# ----------------------------------------------------------- local data


def test_csv_roundtrip_applies_read_options(tmp_path):
    store = make_store(tmp_path)
    store.save_data("raw", "listings.csv", sample_df())

    df = store.load_data(
        "raw",
        "listings.csv",
        columns=["id", "city", "day"],
        dtypes={"city": "category"},
        parse_dates=["day"],
    )

    assert list(df.columns) == ["id", "city", "day"]
    assert str(df["city"].dtype) == "category"
    assert pd.api.types.is_datetime64_any_dtype(df["day"])


@pytest.mark.parametrize("name", ["clean.parquet", "clean.json", "clean.jsonl"])
def test_roundtrip_by_extension(tmp_path, name):
    store = make_store(tmp_path)
    store.save_data("processed", name, sample_df())

    df = store.load_data(
        "processed", name, columns=["id", "price", "day"], parse_dates=["day"]
    )

    assert df["id"].tolist() == [1, 2, 3]
    assert pd.api.types.is_datetime64_any_dtype(df["day"])


def test_dask_parquet_roundtrip(tmp_path):
    dd = pytest.importorskip("dask.dataframe")
    store = make_store(tmp_path)
    store.save_data(
        "processed", "events.parquet", dd.from_pandas(sample_df(), npartitions=2)
    )

    df = store.load_data("processed", "events.parquet", engine="dask", columns=["id"])

    assert type(df).__module__.startswith("dask")
    assert sorted(df.compute()["id"]) == [1, 2, 3]


def test_missing_file_with_sync_off_does_not_touch_s3(tmp_path):
    store = make_store(tmp_path)

    with pytest.raises(FileNotFoundError, match="sync_s3 is off"):
        store.load_data("raw", "missing.csv")
    assert store._s3 is None


# ----------------------------------------------------------- artifacts


def test_artifact_writer_and_reader(tmp_path):
    store = make_store(tmp_path)

    path = store.save_artifact(
        "analytics", "eda/report.html", writer=lambda p: p.write_text("<html/>")
    )

    assert path == store.path("analytics", "eda/report.html")
    assert store.load_artifact("analytics", "eda/report.html") == path
    assert (
        store.load_artifact(
            "analytics", "eda/report.html", reader=lambda p: p.read_text()
        )
        == "<html/>"
    )


def test_writer_that_writes_nothing_is_an_error(tmp_path):
    store = make_store(tmp_path)

    with pytest.raises(RuntimeError, match="Nothing was written"):
        store.save_artifact("analytics", "x.txt", writer=lambda p: None)
    assert not list((tmp_path / "data").rglob("*x.txt"))


def test_failed_write_keeps_previous_version_and_no_temp_files(tmp_path):
    store = make_store(tmp_path)
    store.save_artifact("analytics", "x.txt", writer=lambda p: p.write_text("v1"))

    def broken_writer(path):
        path.write_text("partial")
        raise OSError("disk full")

    with pytest.raises(OSError):
        store.save_artifact("analytics", "x.txt", writer=broken_writer)

    folder = store.path("analytics")
    assert (folder / "x.txt").read_text() == "v1"
    assert [p.name for p in folder.iterdir()] == ["x.txt"]


def test_folder_artifact_replaces_previous_folder(tmp_path):
    store = make_store(tmp_path)

    def writer(files):
        def write(path):
            path.mkdir()
            for file in files:
                (path / file).write_text(file)

        return write

    store.save_artifact("models", "m", writer=writer(["a", "b"]))
    path = store.save_artifact("models", "m", writer=writer(["a"]))

    assert sorted(p.name for p in path.iterdir()) == ["a"]


# ----------------------------------------------------------------- S3


def test_save_uploads_to_location_bucket_and_prefix(tmp_path, s3):
    store = make_store(tmp_path, sync_s3=True)

    store.save_data("processed", "clean.csv", sample_df())
    store.save_artifact("analytics", "eda/r.html", writer=lambda p: p.write_text("x"))

    assert s3_keys(s3, BUCKET) == ["ml/project/processed/clean.csv"]
    assert s3_keys(s3, ANALYTICS_BUCKET) == ["team-x/project/eda/r.html"]


def test_sync_false_keeps_a_save_local(tmp_path, s3):
    store = make_store(tmp_path, sync_s3=True)

    path = store.save_data("processed", "clean.csv", sample_df(), sync=False)

    assert path.exists()
    assert s3_keys(s3, BUCKET) == []


def test_sync_off_never_uploads(tmp_path, s3):
    store = make_store(tmp_path, sync_s3=False)

    store.save_data("processed", "clean.csv", sample_df())

    assert s3_keys(s3, BUCKET) == []


def test_load_downloads_a_missing_file(tmp_path, s3):
    s3.put_object(
        Bucket=BUCKET,
        Key="ml/project/raw/listings.csv",
        Body=sample_df().to_csv(index=False),
    )
    store = make_store(tmp_path, sync_s3=True)

    df = store.load_data("raw", "listings.csv")

    assert df["id"].tolist() == [1, 2, 3]
    assert store.path("raw", "listings.csv").exists()


def test_local_file_wins_over_s3(tmp_path, s3):
    s3.put_object(Bucket=BUCKET, Key="ml/project/raw/x.txt", Body=b"remote")
    store = make_store(tmp_path, sync_s3=True)
    store.save_artifact(
        "raw", "x.txt", writer=lambda p: p.write_text("local"), sync=False
    )

    assert (
        store.load_artifact("raw", "x.txt", reader=lambda p: p.read_text()) == "local"
    )


def test_missing_everywhere_names_both_places(tmp_path, s3):
    store = make_store(tmp_path, sync_s3=True)

    with pytest.raises(
        FileNotFoundError, match="s3://ml-bucket/ml/project/raw/nope.csv"
    ):
        store.load_data("raw", "nope.csv")


def test_folder_upload_mirrors_and_downloads(tmp_path, s3):
    store = make_store(tmp_path, sync_s3=True)

    def writer(files):
        def write(path):
            path.mkdir()
            for file in files:
                (path / file).write_text(file)

        return write

    store.save_artifact("models", "m", writer=writer(["a.txt", "b.txt"]))
    store.save_artifact("models", "m", writer=writer(["a.txt"]))
    assert s3_keys(s3, BUCKET) == ["ml/project/models/m/a.txt"]

    store.save_artifact("models", "m", writer=writer(["a.txt"]), sync=False)
    path = store.path("models", "m")
    for file in path.iterdir():
        file.unlink()
    path.rmdir()

    restored = store.load_artifact("models", "m")
    assert sorted(p.name for p in restored.iterdir()) == ["a.txt"]


def test_glob_downloads_matching_files(tmp_path, s3):
    for key in ("events/1.csv", "events/2.csv", "events/readme.md", "other/3.csv"):
        s3.put_object(Bucket=BUCKET, Key=f"ml/project/raw/{key}", Body=b"id\n1\n")
    store = make_store(tmp_path, sync_s3=True)

    store.load_artifact("raw", "events/*.csv")

    local = store.path("raw")
    assert sorted(p.relative_to(local).as_posix() for p in local.rglob("*.*")) == [
        "events/1.csv",
        "events/2.csv",
    ]


# -------------------------------------------------------------- config


def test_from_env_reads_the_dumped_config(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    monkeypatch.setenv(STORE_CONFIG_ENV, store.dump(tmp_path / "store.yaml"))

    assert Store.from_env().to_dict() == store.to_dict()


def test_from_env_finds_the_project_config_from_a_step_folder(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text(
        "root: ${oc.env:PROJECT_ROOT,.}\n"
        "store:\n"
        "  local_root: ${root}/data\n"
        "  locations:\n"
        "    raw:\n"
        "      path: raw\n"
    )
    step_folder = tmp_path / "src" / "basic_cleaning"
    step_folder.mkdir(parents=True)
    monkeypatch.delenv(STORE_CONFIG_ENV, raising=False)
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    monkeypatch.chdir(step_folder)

    assert Store.from_env().path("raw") == (tmp_path / "data" / "raw").resolve()


def test_project_config_builds_a_store(monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", PROJECT_ROOT)
    config = OmegaConf.load(os.path.join(PROJECT_ROOT, "config.yaml"))

    store = Store.from_config(config.store)

    assert store.path("raw") == Path(PROJECT_ROOT).resolve() / "data" / "raw"
    assert store.path("models") == Path(PROJECT_ROOT).resolve() / "models"
