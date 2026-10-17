"""
Remote copy of the store's locations.

RemoteStorage implements the logic the store relies on (download a file or a
whole folder atomically, mirror a folder on upload) on top of five primitives.
To support another backend (GCS, Azure...), subclass it, implement those
primitives and pass an instance to the store: Store(..., remote=GCSStorage()).
"""

from abc import ABC, abstractmethod
from pathlib import Path

from utils.files import remove_path, replace_path, tmp_sibling


class RemoteStorage(ABC):
    # URI scheme used in logs and error messages, e.g. "s3"
    scheme: str = "remote"

    # ------------------------------------------------------------- primitives

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool:
        """True if `key` is an object (a file, not a folder prefix)."""

    @abstractmethod
    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        """Every object key that starts with `prefix`."""

    @abstractmethod
    def get_file(self, bucket: str, key: str, local: Path) -> None:
        """Download one object to `local`."""

    @abstractmethod
    def put_file(self, local: Path, bucket: str, key: str) -> None:
        """Upload one local file to `key`."""

    @abstractmethod
    def delete_keys(self, bucket: str, keys: list[str]) -> None:
        """Delete the given objects."""

    # ------------------------------------------------------- store operations

    def uri(self, bucket: str, key: str) -> str:
        return f"{self.scheme}://{bucket}/{key}"

    def download_file(self, bucket: str, key: str, local: Path) -> None:
        """Download one object to `local`; `local` only appears once complete."""
        local.parent.mkdir(parents=True, exist_ok=True)
        tmp = tmp_sibling(local)
        try:
            self.get_file(bucket, key, tmp)
            replace_path(tmp, local)
        finally:
            remove_path(tmp)

    def download(self, bucket: str, key: str, local: Path) -> bool:
        """
        Download `key` to `local`. If `key` is not an object, every object under
        `key/` is downloaded as a folder. Returns False when nothing exists.
        """
        if self.exists(bucket, key):
            self.download_file(bucket, key, local)
            return True

        prefix = key.rstrip("/") + "/"
        keys = [k for k in self.list_keys(bucket, prefix) if not k.endswith("/")]
        if not keys:
            return False

        local.parent.mkdir(parents=True, exist_ok=True)
        tmp = tmp_sibling(local)
        try:
            for k in keys:
                target = tmp / k[len(prefix) :]
                target.parent.mkdir(parents=True, exist_ok=True)
                self.get_file(bucket, k, target)
            replace_path(tmp, local)
        finally:
            remove_path(tmp)
        return True

    def upload(self, local: Path, bucket: str, key: str) -> None:
        """
        Upload a file to `key`, or mirror a folder to `key/`: objects under `key/`
        that no longer exist locally are deleted, so a re-saved dask dataset with
        fewer partitions doesn't keep stale part files.
        """
        if local.is_file():
            self.put_file(local, bucket, key)
            return

        prefix = key.rstrip("/") + "/"
        uploaded = set()
        for file in sorted(p for p in local.rglob("*") if p.is_file()):
            file_key = prefix + file.relative_to(local).as_posix()
            self.put_file(file, bucket, file_key)
            uploaded.add(file_key)

        stale = [k for k in self.list_keys(bucket, prefix) if k not in uploaded]
        if stale:
            self.delete_keys(bucket, stale)


class S3Storage(RemoteStorage):
    """
    S3 (or any S3-compatible endpoint) through boto3. boto3 is imported on first
    use, so a store with sync disabled never needs AWS libraries, credentials or
    network.
    """

    scheme = "s3"

    def __init__(self, profile=None, region=None, endpoint_url=None):
        # Empty env values (e.g. AWS_PROFILE=) mean "not set"
        self.profile = profile or None
        self.region = region or None
        self.endpoint_url = endpoint_url or None
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import boto3

            session = boto3.Session(profile_name=self.profile, region_name=self.region)
            self._client = session.client("s3", endpoint_url=self.endpoint_url)
        return self._client

    def exists(self, bucket: str, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as err:
            if err.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys

    def get_file(self, bucket: str, key: str, local: Path) -> None:
        self.client.download_file(bucket, key, str(local))

    def put_file(self, local: Path, bucket: str, key: str) -> None:
        self.client.upload_file(str(local), bucket, key)

    def delete_keys(self, bucket: str, keys: list[str]) -> None:
        for start in range(0, len(keys), 1000):
            batch = keys[start : start + 1000]
            self.client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [dict(Key=k) for k in batch]},
            )
