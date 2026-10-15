"""
Read and write DataFrames with pandas or dask. The file format comes from the
name's extension unless `format` is given.
"""

from pathlib import Path

ENGINES = ("pandas", "dask")
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


def is_dask(df) -> bool:
    return type(df).__module__.startswith("dask")


def read(
    path: str,
    engine: str,
    fmt: str,
    columns=None,
    dtypes=None,
    parse_dates=None,
    **options,
):
    lib = _lib(engine)

    if Path(path).is_dir() and fmt in ("csv", "json"):
        if engine == "pandas":
            raise ValueError(
                f"{path} is a folder of {fmt} files; read it with engine='dask'"
            )
        path = str(Path(path) / "*")

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


def write(df, path: str, fmt: str, **options):
    dask = is_dask(df)

    if fmt == "csv":
        options.setdefault("index", False)
        if dask:
            options.setdefault("single_file", True)
        df.to_csv(path, **options)
    elif fmt == "parquet":
        df.to_parquet(path, **options)
    else:
        options.setdefault("orient", "records")
        if dask or path.endswith(".jsonl"):
            options.setdefault("lines", True)
        df.to_json(path, **options)


def _lib(engine: str):
    if engine == "pandas":
        import pandas

        return pandas
    if engine == "dask":
        import dask.dataframe

        return dask.dataframe
    raise ValueError(f"Unknown engine {engine!r}. Use one of {list(ENGINES)}")


def _not_none(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}
