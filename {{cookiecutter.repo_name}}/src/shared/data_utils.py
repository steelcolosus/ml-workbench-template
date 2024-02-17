from datetime import date, datetime

import mlflow
import pandas as pd
from ydata_profiling import ProfileReport


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


def apply_aggregations(data: pd.DataFrame, config: dict) -> pd.DataFrame:
    aggregations = {}
    custom_functions = {}

    if 'custom_functions' in config:
        custom_functions = {
            func['name']: func for func in config['custom_functions']
        }
    for agg in config['aggregations']:
        column = agg['column']
        name = agg['name']
        aggfunc = agg['aggfunc']
        if aggfunc in custom_functions:
            custom_func = custom_functions[aggfunc]
            condition = custom_func['condition']
            true_value = custom_func['true_value']
            false_value = custom_func['false_value']
            def aggfunc(x): return true_value if (
                x == condition).any() else false_value
        aggregations[name] = pd.NamedAgg(column=column, aggfunc=aggfunc)

    groupby_columns = config['groupby']
    for date_column in config['date_columns']:
        if date_column in groupby_columns:
            groupby_columns.remove(date_column)
            groupby_columns.append(data[date_column].dt.date)

    data = data.groupby(groupby_columns).agg(**aggregations).reset_index()

    return data


def generate_custom_features(data: pd.DataFrame, config: dict) -> pd.DataFrame:

    for feature in config['custom_features']:
        operation = feature['operation']
        name = feature['name']
        if operation == 'subtract':
            data[name] = data[feature['columns'][0]]
            for column in feature['columns'][1:]:
                data[name] -= data[column]
        elif operation == 'fillna':
            data[name] = data[name].fillna(feature['value'])
        elif operation == 'divide':
            data[name] = data.apply(lambda row:
                                    row[feature['columns'][0]] /
                                    row[feature['columns'][1]]
                                    if row[feature['columns'][1]] != 0 else 0,
                                    axis=1)
            if 'fillna' in feature:
                data[name] = data[name].fillna(feature['fillna'])
        elif operation == 'diff':
            data[name] = data[feature['column']
                              ].diff().fillna(feature['fillna'])
        elif operation == 'rolling_mean':
            data[name] = data[feature['column']].rolling(
                window=feature['window']).mean().fillna(data[feature['column']])

    return data


def generate_date_features(data: pd.DataFrame, config: str) -> pd.DataFrame:
    date_column = config['date_columns'][0]

    if not date_column:
        print("No date column found")
        return data

    data[date_column] = pd.to_datetime(data[date_column])

    for feature in config['date_features']:
        operation = feature['operation']
        name = feature['name']
        if operation == 'dayofweek':
            data[name] = data[feature['column']].dt.dayofweek
        elif operation == 'is_weekend':
            data[name] = data[feature['column']].apply(
                lambda x: 1 if x >= 5 else 0)
        elif operation == 'month':
            data[name] = data[feature['column']].dt.month
        elif operation == 'quarter':
            data[name] = data[feature['column']].dt.quarter
        elif operation == 'year':
            data[name] = data[feature['column']].dt.year

    return data


def generate_eda_report(data: pd.DataFrame, title: str, output_path: str):

    profile = ProfileReport(
        data,
        title=title
    )
    profile.to_file(output_path)


def generate_heatmap(data: pd.DataFrame, output_path: str):
    import matplotlib.pyplot as plt
    import seaborn as sns

    numeric_columns = data.select_dtypes(
        include=['int32', 'int64', 'float64']
    ).columns

    corr = data[numeric_columns].corr()

    plt.figure(figsize=(12, 10))
    sns.heatmap(corr, annot=True, cmap=plt.cm.Reds)
    plt.savefig(output_path)


def apply_filters(data: pd.DataFrame, config: dict) -> pd.DataFrame:

    for filter in config['filters']:
        column = filter['column']
        value = filter['value']
        data = data[data[column] == value]

    for suffix in config['exclude_suffixes']:
        data = data[[col for col in data.columns if not col.endswith(suffix)]]

    return data


def convert_to_date(data: pd.DataFrame, columns: list) -> pd.DataFrame:
    for col in columns:
        data[col] = pd.to_datetime(data[col])

    return data
