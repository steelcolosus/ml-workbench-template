from omegaconf import OmegaConf

from utils.config import load_project_config, serialize_config


def test_serialize_config_resolves_references(tmp_path):
    config = OmegaConf.create(
        dict(
            first=dict(output_artifact="clean.parquet"),
            second=dict(input_artifact="${first.output_artifact}"),
        )
    )

    path = serialize_config(config.second, tmp_path / "second.yaml")

    assert OmegaConf.load(path) == dict(input_artifact="clean.parquet")


def test_a_relative_root_is_resolved_from_the_config_folder(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text(
        "root: ${oc.env:PROJECT_ROOT,.}\nmodels: ${root}/models\n"
    )
    elsewhere = tmp_path / "src" / "steps" / "step"
    elsewhere.mkdir(parents=True)
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    monkeypatch.chdir(elsewhere)

    config = load_project_config()

    assert config.models == str(tmp_path.resolve() / "models")
