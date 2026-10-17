"""
DataFrame engines used by Store.load_data and Store.save_data.

A DataEngine reads and writes one kind of DataFrame in the formats the store
supports (csv, parquet, json). The file format comes from the name's extension
unless `format` is given. To add an engine (polars, ...), subclass DataEngine
and pass it to the store: Store(..., engines={"polars": PolarsEngine()}).
"""

from abc import ABC, abstractmethod
from pathlib import Path

FORMATS = {
    ".csv": "csv",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".json": "json",
    ".jsonl": "json",
}


def infer_format(name: str, fmt: str = None) -> str:
    if fmt:
        if fmt not in set(FORMATS.values()):
            raise ValueError(
                f"Unsupported format {fmt!r}. Use one of: csv, parquet, json"
            )
        return fmt

    suffix = Path(name.rstrip("/")).suffix.lower()
    if suffix not in FORMATS:
        raise ValueError(
            f"Can't infer the data format of {name!r}. Use one of the extensions "
            f"{sorted(FORMATS)} or pass format='csv' | 'parquet' | 'json'"
        )
    return FORMATS[suffix]


class DataEngine(ABC):
    @abstractmethod
    def owns(self, df) -> bool:
        """True if `df` is this engine's DataFrame type (save_data picks by it)."""

    @abstractmethod
    def read(
        self,
        path: str,
        fmt: str,
        columns: list = None,
        dtypes: dict = None,
        parse_dates: list = None,
        **options,
    ):
        """
        Read `path`. `columns`, `dtypes` and `parse_dates` must behave the same
        for every format; other options go to the underlying reader.
        """

    @abstractmethod
    def write(self, df, path: str, fmt: str, **options) -> None:
        """Write `df` to `path`; options go to the underlying writer."""


class PandasEngine(DataEngine):
    def owns(self, df) -> bool:
        import pandas

        return isinstance(df, pandas.DataFrame)

    def read(self, path, fmt, columns=None, dtypes=None, parse_dates=None, **options):
        import pandas

        if Path(path).is_dir() and fmt in ("csv", "json"):
            raise ValueError(
                f"{path} is a folder of {fmt} files; read it with engine='dask'"
            )
        return _read(pandas, path, fmt, columns, dtypes, parse_dates, options)

    def write(self, df, path, fmt, **options):
        if fmt == "json" and path.endswith(".jsonl"):
            options.setdefault("lines", True)
        _write(df, path, fmt, options)


class DaskEngine(DataEngine):
    """Large datasets: `name` may be a folder or a glob such as "events/*.csv"."""

    def owns(self, df) -> bool:
        return type(df).__module__.startswith("dask")

    def read(self, path, fmt, columns=None, dtypes=None, parse_dates=None, **options):
        import dask.dataframe

        if Path(path).is_dir() and fmt in ("csv", "json"):
            path = str(Path(path) / "*")
        return _read(dask.dataframe, path, fmt, columns, dtypes, parse_dates, options)

    def write(self, df, path, fmt, **options):
        if fmt == "csv":
            options.setdefault("single_file", True)
        if fmt == "json":
            options.setdefault("lines", True)
        _write(df, path, fmt, options)


def default_engines() -> dict:
    return {"pandas": PandasEngine(), "dask": DaskEngine()}


def _read(lib, path, fmt, columns, dtypes, parse_dates, options):
    """Shared by pandas and dask, which have the same reader API."""
    if fmt == "csv":
        return lib.read_csv(
            path,
            **_not_none(usecols=columns, dtype=dtypes, parse_dates=parse_dates),
            **options,
        )

    if fmt == "parquet":
        df = lib.read_parquet(path, **_not_none(columns=columns), **options)
    else:
        if path.endswith(".jsonl"):
            options.setdefault("lines", True)
            options.setdefault("orient", "records")
        df = lib.read_json(path, **options)
        if columns:
            df = df[list(columns)]

    if dtypes:
        df = df.astype(dict(dtypes))
    for column in parse_dates or []:
        df[column] = lib.to_datetime(df[column])
    return df


def _write(df, path, fmt, options):
    """Shared by pandas and dask, which have the same writer API."""
    if fmt == "csv":
        options.setdefault("index", False)
        df.to_csv(path, **options)
    elif fmt == "parquet":
        df.to_parquet(path, **options)
    else:
        options.setdefault("orient", "records")
        df.to_json(path, **options)


def _not_none(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}
