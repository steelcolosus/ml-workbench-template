from datetime import date, datetime

import mlflow
import pandas as pd


def log_dataset(data, path, name, context):
    dataset = mlflow.data.from_pandas(data, source=path)
    mlflow.log_input(dataset, name, context=context)


def convert_timestamps(obj):
    if isinstance(obj, dict):
        for key in obj:
            obj[key] = convert_timestamps(obj[key])
    elif isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    return obj


def describe_data(data: pd.DataFrame, name) -> pd.DataFrame:
    """
    Describe a pandas dataframe
    """
    describe_to_dict = data.describe().to_dict()

    # Convert Timestamp objects to string in the nested dictionary
    describe_to_dict = convert_timestamps(describe_to_dict)

    mlflow.log_dict(describe_to_dict, name)


def _condition_aggregation(condition, true_value, false_value):
    # Built in its own scope so each aggregation keeps its own values
    def aggfunc(x):
        return true_value if (x == condition).any() else false_value

    return aggfunc


def apply_aggregations(data: pd.DataFrame, config: dict) -> pd.DataFrame:
    aggregations = {}
    custom_functions = {}

    if "custom_functions" in config:
        custom_functions = {func["name"]: func for func in config["custom_functions"]}
    for agg in config["aggregations"]:
        column = agg["column"]
        name = agg["name"]
        aggfunc = agg["aggfunc"]
        if aggfunc in custom_functions:
            custom_func = custom_functions[aggfunc]
            aggfunc = _condition_aggregation(
                custom_func["condition"],
                custom_func["true_value"],
                custom_func["false_value"],
            )
        aggregations[name] = pd.NamedAgg(column=column, aggfunc=aggfunc)

    # Copy so the config's groupby list is not modified
    groupby_columns = list(config["groupby"])
    for date_column in config.get("date_columns", []):
        if date_column in groupby_columns:
            groupby_columns.remove(date_column)
            groupby_columns.append(data[date_column].dt.date)

    data = data.groupby(groupby_columns).agg(**aggregations).reset_index()

    return data


def generate_custom_features(data: pd.DataFrame, config: dict) -> pd.DataFrame:

    for feature in config["custom_features"]:
        operation = feature["operation"]
        name = feature["name"]
        if operation == "subtract":
            data[name] = data[feature["columns"][0]]
            for column in feature["columns"][1:]:
                data[name] -= data[column]
        elif operation == "fillna":
            data[name] = data[name].fillna(feature["value"])
        elif operation == "divide":
            numerator, denominator = feature["columns"][:2]
            data[name] = (data[numerator] / data[denominator]).where(
                data[denominator] != 0, 0
            )
            if "fillna" in feature:
                data[name] = data[name].fillna(feature["fillna"])
        elif operation == "diff":
            data[name] = data[feature["column"]].diff().fillna(feature["fillna"])
        elif operation == "rolling_mean":
            data[name] = (
                data[feature["column"]]
                .rolling(window=feature["window"])
                .mean()
                .fillna(data[feature["column"]])
            )

    return data


def generate_date_features(data: pd.DataFrame, config: str) -> pd.DataFrame:
    date_column = config["date_columns"][0]

    if not date_column:
        print("No date column found")
        return data

    data[date_column] = pd.to_datetime(data[date_column])

    for feature in config["date_features"]:
        operation = feature["operation"]
        name = feature["name"]
        if operation == "dayofweek":
            data[name] = data[feature["column"]].dt.dayofweek
        elif operation == "is_weekend":
            data[name] = data[feature["column"]].apply(lambda x: 1 if x >= 5 else 0)
        elif operation == "month":
            data[name] = data[feature["column"]].dt.month
        elif operation == "quarter":
            data[name] = data[feature["column"]].dt.quarter
        elif operation == "year":
            data[name] = data[feature["column"]].dt.year

    return data


def generate_eda_report(data: pd.DataFrame, title: str, output_path: str):
    # Imported here: ydata_profiling is slow to import
    from ydata_profiling import ProfileReport

    profile = ProfileReport(data, title=title)
    profile.to_file(output_path)


def generate_heatmap(data: pd.DataFrame, output_path: str):
    import matplotlib.pyplot as plt
    import seaborn as sns

    numeric_columns = data.select_dtypes(include="number").columns

    corr = data[numeric_columns].corr()

    fig = plt.figure(figsize=(12, 10))
    sns.heatmap(corr, annot=True, cmap=plt.cm.Reds)
    fig.savefig(output_path)
    plt.close(fig)


def apply_filters(data: pd.DataFrame, config: dict) -> pd.DataFrame:

    for filter in config["filters"]:
        column = filter["column"]
        value = filter["value"]
        data = data[data[column] == value]

    for suffix in config["exclude_suffixes"]:
        data = data[[col for col in data.columns if not col.endswith(suffix)]]

    return data


def convert_to_date(data: pd.DataFrame, columns: list) -> pd.DataFrame:
    for col in columns:
        data[col] = pd.to_datetime(data[col])

    return data
