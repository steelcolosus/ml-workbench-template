from omegaconf import OmegaConf

from utils.config import serialize_config


def test_serialize_config_resolves_references(tmp_path):
    config = OmegaConf.create(
        dict(
            first=dict(output_artifact="clean.parquet"),
            second=dict(input_artifact="${first.output_artifact}"),
        )
    )

    path = serialize_config(config.second, tmp_path / "second.yaml")

    assert OmegaConf.load(path) == dict(input_artifact="clean.parquet")
