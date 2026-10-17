"""Exploratory data analysis helpers that log to MLflow or write reports."""

import mlflow
import pandas as pd

from utils.serialization import convert_timestamps


def log_dataset(data, path, name, context):
    dataset = mlflow.data.from_pandas(data, source=path)
    mlflow.log_input(dataset, name, context=context)


def describe_data(data: pd.DataFrame, name) -> None:
    """
    Describe a pandas dataframe
    """
    describe_to_dict = data.describe().to_dict()

    # Convert Timestamp objects to string in the nested dictionary
    describe_to_dict = convert_timestamps(describe_to_dict)

    mlflow.log_dict(describe_to_dict, name)


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
