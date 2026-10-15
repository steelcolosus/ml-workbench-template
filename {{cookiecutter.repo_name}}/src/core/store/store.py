"""
Local-first store for pipeline data and artifacts, with optional S3 sync.

Every call takes a `location` (a folder configured under `store.locations`) and a
`name` inside it. Files are always read from and written to the local folder.
When `store.sync_s3` is true, a file that is missing locally is downloaded on
load, and every save is uploaded afterwards (unless the call passes sync=False).

S3 path of an item:
    s3://<bucket>/<prefix>/<name>
where <bucket> is the location's bucket or store.bucket, and <prefix> is the
location's prefix or store.prefix/<location name>.

Extension points (see remote.py and engines.py):
    Store(..., remote=MyStorage())             another remote backend
    Store(..., engines={"polars": MyEngine()}) another DataFrame engine
"""

import glob
import os
from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import yaml

from core.store.engines import DataEngine, default_engines, infer_format
from core.store.remote import RemoteStorage, S3Storage
from utils.files import remove_path, replace_path, tmp_sibling
from utils.log import get_logger

logger = get_logger("STORE")

# Path of a YAML file with the resolved store config. main.py sets it so that
# steps launched with `mlflow run` see the same config, CLI overrides included.
STORE_CONFIG_ENV = "STORE_CONFIG"
PROJECT_CONFIG = "config.yaml"
LOCATION_KEYS = {"path", "bucket", "prefix"}


@dataclass(frozen=True)
class Location:
    name: str
    path: Path
    bucket: str | None
    prefix: str

    def key(self, name: str) -> str:
        return "/".join(part for part in (self.prefix, name) if part)


class Store:
    """
    Usage:
        store = Store.from_env()

        df = store.load_data("raw", "listings.csv", columns=["id", "price"])
        store.save_data("processed", "clean.parquet", df)

        store.save_artifact("analytics", "eda/report.html",
                            writer=lambda path: report.to_file(path))
        model = store.load_artifact("models", "price_model",
                                    reader=mlflow.pyfunc.load_model)

        path = store.path("analytics", "plots/heatmap.png")  # path only, no sync
    """

    def __init__(
        self,
        local_root,
        locations: dict,
        sync_s3: bool = False,
        bucket: str = None,
        prefix: str = "",
        aws_profile: str = None,
        region: str = None,
        endpoint_url: str = None,
        base_dir=None,
        remote: RemoteStorage = None,
        engines: dict[str, DataEngine] = None,
    ):
        base = Path(base_dir or os.getcwd()).resolve()
        self.local_root = _absolute(local_root, base)
        self.sync_s3 = bool(sync_s3)
        self.bucket = _clean_bucket(bucket)
        self.prefix = _clean_prefix(prefix)
        self._s3_settings = {
            "profile": aws_profile,
            "region": region,
            "endpoint_url": endpoint_url,
        }
        # Built on first use (S3Storage by default), so sync off needs no AWS setup
        self._remote = remote
        self.engines = {**default_engines(), **(engines or {})}

        if not locations:
            raise ValueError("store.locations is empty: configure at least one")

        self.locations = {}
        for name, spec in locations.items():
            spec = dict(spec or {})
            unknown = set(spec) - LOCATION_KEYS
            if unknown:
                raise ValueError(
                    f"Unknown keys {sorted(unknown)} in store.locations.{name}. "
                    f"Allowed: {sorted(LOCATION_KEYS)}"
                )
            prefix_ = spec.get("prefix")
            self.locations[name] = Location(
                name=name,
                path=_absolute(spec.get("path") or name, self.local_root),
                bucket=_clean_bucket(spec.get("bucket")) or self.bucket,
                prefix=(
                    _clean_prefix(prefix_)
                    if prefix_ is not None
                    else _clean_prefix(f"{self.prefix}/{name}")
                ),
            )

        if self.sync_s3:
            missing = sorted(n for n, loc in self.locations.items() if not loc.bucket)
            if missing:
                raise ValueError(
                    f"store.sync_s3 is true but locations {missing} have no bucket. "
                    "Set store.bucket (AWS_BUCKET) or a bucket on each location."
                )

    # ------------------------------------------------------------------ setup

    @classmethod
    def from_config(cls, config, base_dir=None, **kwargs) -> "Store":
        """
        Build a store from the `store` config section (dict or OmegaConf node).
        Relative paths are resolved against `base_dir` (default: cwd). Other
        keyword arguments (remote, engines) go to the constructor.
        """
        from omegaconf import OmegaConf

        if OmegaConf.is_config(config):
            config = OmegaConf.to_container(config, resolve=True)
        return cls(**config, base_dir=base_dir, **kwargs)

    @classmethod
    def from_env(cls, **kwargs) -> "Store":
        """
        Build the store inside a step: from $STORE_CONFIG when the step is launched
        by main.py, otherwise from the project's config.yaml (searched upwards from
        $PROJECT_ROOT or the current directory), so steps also run on their own.
        Keyword arguments (remote, engines) go to the constructor.
        """
        from omegaconf import OmegaConf

        config_file = os.environ.get(STORE_CONFIG_ENV)
        if config_file:
            return cls.from_config(
                OmegaConf.load(config_file), base_dir=Path(config_file).parent, **kwargs
            )

        project_config = _find_project_config()
        config = OmegaConf.load(project_config)
        return cls.from_config(config.store, base_dir=project_config.parent, **kwargs)

    def to_dict(self) -> dict:
        """Resolved config with absolute paths, accepted by `from_config`."""
        return {
            "local_root": str(self.local_root),
            "sync_s3": self.sync_s3,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "aws_profile": self._s3_settings["profile"],
            "region": self._s3_settings["region"],
            "endpoint_url": self._s3_settings["endpoint_url"],
            "locations": {
                name: {
                    "path": str(loc.path),
                    "bucket": loc.bucket,
                    "prefix": loc.prefix,
                }
                for name, loc in self.locations.items()
            },
        }

    def dump(self, path) -> str:
        """Write `to_dict()` as YAML (for $STORE_CONFIG) and return the path."""
        with open(path, "w") as fp:
            yaml.safe_dump(self.to_dict(), fp, sort_keys=False)
        return str(path)

    # ------------------------------------------------------------------- paths

    def path(self, location: str, name: str = "") -> Path:
        """Local path of `name` inside `location`. No download or upload."""
        loc = self._location(location)
        name = _clean_name(name)
        return loc.path / name if name else loc.path

    def uri(self, location: str, name: str = "") -> str | None:
        """Remote URI of `name` inside `location`, or None if it has no bucket."""
        loc = self._location(location)
        if not loc.bucket:
            return None
        return self.remote.uri(loc.bucket, loc.key(_clean_name(name)))

    # -------------------------------------------------------------------- data

    def load_data(
        self,
        location: str,
        name: str,
        engine: str = "pandas",
        columns: list = None,
        dtypes: dict = None,
        parse_dates: list = None,
        format: str = None,
        **read_options,
    ):
        """
        Read a DataFrame with one of `self.engines` (pandas, dask, ...).
        `columns`, `dtypes` and `parse_dates` work the same for every format; other
        keyword arguments go to the reader (e.g. sep=";" for csv, blocksize="128MB"
        for dask). With dask, `name` may be a glob such as "events/*.parquet" or a
        folder.
        """
        data_engine = self._engine(engine)
        fmt = infer_format(name, format)
        path = self._ensure_local(location, name)
        return data_engine.read(
            str(path),
            fmt,
            columns=columns,
            dtypes=dtypes,
            parse_dates=parse_dates,
            **read_options,
        )

    def save_data(
        self,
        location: str,
        name: str,
        df,
        format: str = None,
        sync: bool = True,
        **write_options,
    ) -> Path:
        """
        Write a DataFrame with the engine that owns its type (pandas, dask, ...).
        Keyword arguments go to the writer. sync=False keeps this save local even
        when store.sync_s3 is on.
        """
        data_engine = next((e for e in self.engines.values() if e.owns(df)), None)
        if data_engine is None:
            raise TypeError(
                f"No engine for {type(df).__name__}. Engines: {sorted(self.engines)}"
            )
        fmt = infer_format(name, format)
        return self._write(
            location,
            name,
            lambda path: data_engine.write(df, str(path), fmt, **write_options),
            sync,
        )

    # --------------------------------------------------------------- artifacts

    def load_artifact(
        self, location: str, name: str, reader: Callable[[Path], Any] = None
    ):
        """
        Make sure the file/folder exists locally (downloading it if needed) and
        return `reader(path)`, or the local path when no reader is given.
        """
        path = self._ensure_local(location, name)
        return reader(path) if reader else path

    def save_artifact(
        self, location: str, name: str, writer: Callable[[Path], Any], sync: bool = True
    ) -> Path:
        """
        Call `writer(path)` to create the file/folder, move it into place and
        upload it when sync is on. sync=False keeps this save local even when
        store.sync_s3 is on. Returns the local path.
        """
        return self._write(location, name, writer, sync)

    # ---------------------------------------------------------------- internal

    @property
    def remote(self) -> RemoteStorage:
        if self._remote is None:
            self._remote = S3Storage(**self._s3_settings)
        return self._remote

    def _engine(self, engine: str) -> DataEngine:
        if engine not in self.engines:
            raise ValueError(
                f"Unknown engine {engine!r}. Engines: {sorted(self.engines)}"
            )
        return self.engines[engine]

    def _location(self, location: str) -> Location:
        if location not in self.locations:
            raise ValueError(
                f"Unknown store location {location!r}. "
                f"Configured locations: {sorted(self.locations)}"
            )
        return self.locations[location]

    def _ensure_local(self, location: str, name: str) -> Path:
        loc = self._location(location)
        name = _clean_name(name)
        local = loc.path / name

        if _is_glob(name):
            if glob.glob(str(local)):
                return local
        elif local.exists():
            return local

        if not self.sync_s3:
            raise FileNotFoundError(
                f"{local} does not exist (store.sync_s3 is off, S3 was not checked)"
            )

        uri = self.remote.uri(loc.bucket, loc.key(name))
        logger.info(f"{local} not found locally, downloading {uri}")
        if _is_glob(name):
            found = self._download_glob(loc, name)
        else:
            found = self.remote.download(loc.bucket, loc.key(name), local)
        if not found:
            raise FileNotFoundError(
                f"{name!r} not found in location {location!r}: "
                f"neither {local} nor {uri} exist"
            )
        return local

    def _download_glob(self, loc: Location, pattern: str) -> bool:
        parts = pattern.split("/")
        static = []
        for part in parts:
            if _is_glob(part):
                break
            static.append(part)

        root = f"{loc.prefix}/" if loc.prefix else ""
        found = False
        for key in self.remote.list_keys(loc.bucket, root + "/".join(static)):
            relative = key[len(root) :]
            segments = relative.split("/")
            if len(segments) == len(parts) and all(
                fnmatchcase(s, p) for s, p in zip(segments, parts, strict=True)
            ):
                self.remote.download_file(loc.bucket, key, loc.path / relative)
                found = True
        return found

    def _write(
        self, location: str, name: str, write: Callable[[Path], Any], sync: bool
    ) -> Path:
        loc = self._location(location)
        name = _clean_name(name)
        if not name:
            raise ValueError("A name is required to save into a location")
        if _is_glob(name):
            raise ValueError(f"Can't save to a glob pattern: {name!r}")

        final = loc.path / name
        final.parent.mkdir(parents=True, exist_ok=True)
        tmp = tmp_sibling(final)
        try:
            write(tmp)
            if not tmp.exists():
                raise RuntimeError(
                    f"Nothing was written for {location}/{name}: the writer must "
                    "create a file or folder at the path it receives"
                )
            replace_path(tmp, final)
        finally:
            remove_path(tmp)

        if self.sync_s3 and sync:
            uri = self.remote.uri(loc.bucket, loc.key(name))
            logger.info(f"Uploading {final} to {uri}")
            self.remote.upload(final, loc.bucket, loc.key(name))
        return final


def _absolute(path, base: Path) -> Path:
    path = Path(os.path.expanduser(str(path)))
    return (path if path.is_absolute() else base / path).resolve()


def _clean_bucket(bucket) -> str | None:
    if not bucket:
        return None
    bucket = str(bucket)
    if bucket.startswith("s3://"):
        bucket = bucket[len("s3://") :]
    bucket = bucket.strip("/")
    if "/" in bucket:
        raise ValueError(
            f"Bucket {bucket!r} contains a path: put only the bucket name in "
            "`bucket` and the rest in `prefix`"
        )
    return bucket


def _clean_prefix(prefix) -> str:
    return "/".join(part for part in str(prefix or "").split("/") if part)


def _clean_name(name) -> str:
    raw = str(name or "").replace("\\", "/")
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if raw.startswith("/") or ".." in parts:
        raise ValueError(
            f"Name must be relative to its location, without '..': {name!r}"
        )
    return "/".join(parts)


def _is_glob(name: str) -> bool:
    return any(char in name for char in "*?[")


def _find_project_config() -> Path:
    from omegaconf import OmegaConf

    start = Path(os.environ.get("PROJECT_ROOT") or os.getcwd()).resolve()
    for folder in (start, *start.parents):
        candidate = folder / PROJECT_CONFIG
        if candidate.is_file() and "store" in OmegaConf.load(candidate):
            return candidate
    raise FileNotFoundError(
        f"No {PROJECT_CONFIG} with a `store` section found in {start} or its "
        f"parents. Run from the project or set ${STORE_CONFIG_ENV}/$PROJECT_ROOT."
    )
