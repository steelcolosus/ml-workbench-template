import datetime
import logging
import os
import shutil

import mlflow.pyfunc
import pandas as pd
from mlflow.models import infer_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger("CUSTOM_MODEL_UTILS")


def get_s3_bucket(s3_path):
    if not s3_path:
        return None

    if "s3://" in s3_path:
        return s3_path.split("/")[2]
    else:
        return s3_path


def save_to_s3(local_file, s3_bucket, s3_key, aws_profile=None):
    """
    Upload local file to s3 using boto3
    """
    import boto3
    session = boto3.Session(profile_name=aws_profile)
    s3 = session.client('s3')
    # today = datetime.date.today().strftime("%Y-%m-%d")
    # s3_key = os.path.join(s3_key, today)
    logger.info(f"Uploading {local_file} to {s3_bucket}/{s3_key}")
    for root, dirs, files in os.walk(local_file):
        for file in files:

            if ".gitkeep" in file:
                continue

            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_file)
            s3_path = os.path.join(s3_key, relative_path)
            s3.upload_file(local_path, s3_bucket, s3_path)

    logger.info(f"Uploaded {local_file} to {s3_bucket}/{s3_key}")


def register_model(run_id, model_name):
    """
    Register model in mlflow

    Args:
        run_id: str
        model_name: str

    Returns:
        None
    """

    mlflow.register_model(
        f"runs:/{run_id}/{model_name}",
        model_name
    )


def save_custom_model(
    model: mlflow.pyfunc.PythonModel,
    model_name,
    save_path,
    code_path,
    sample: pd.DataFrame,
    log_model=True,
    model_params=None,
):

    save_path = os.path.join(save_path, model_name)

    if not os.path.exists(save_path):
        os.makedirs(save_path)
    if os.path.exists(save_path):
        shutil.rmtree(save_path)

    result = model.predict({}, sample)

    signature = infer_signature(sample, result, params=model_params)

    # get sample data for signature
    if log_model:
        mlflow.pyfunc.log_model(
            artifact_path=model_name,
            python_model=model,
            signature=signature,
            code_path=code_path,
        )

    mlflow.pyfunc.save_model(
        path=save_path,
        python_model=model,
        signature=signature,
        code_path=code_path
    )

    s3_bucket = os.environ.get("AWS_BUCKET", None)
    is_training = os.environ.get("TRAINING", None)
    s3_bucket = get_s3_bucket(s3_bucket)
    if s3_bucket and is_training:
        aws_profile = os.environ.get("AWS_PROFILE", None)
        s3_key = os.path.join("ml", "models", model_name)
        save_to_s3(save_path, s3_bucket, s3_key, aws_profile)
