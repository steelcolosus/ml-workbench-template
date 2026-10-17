from pathlib import Path

import pytest
from cookiecutter.main import cookiecutter

TEMPLATE = Path(__file__).resolve().parents[1]


@pytest.fixture
def render(tmp_path):
    """Generate a project into tmp_path and return its folder."""

    def render(**context):
        output = tmp_path / "out"
        project = cookiecutter(
            str(TEMPLATE), no_input=True, extra_context=context, output_dir=output
        )
        return Path(project)

    return render
