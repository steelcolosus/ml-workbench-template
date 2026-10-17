"""Finish the generated project: drop LICENSE when none was chosen, print next steps."""

from pathlib import Path

LICENSE = {{ cookiecutter.open_source_license | tojson }}

if LICENSE == "No license file":
    Path("LICENSE").unlink()

print(f"""
Project created in {Path.cwd()}

Next steps:
    cd {Path.cwd().name}
    make venv      # create .venv with uv (and uv.lock: commit it)
    make test      # check the setup
    make help      # every command

docs/ARCHITECTURE.md explains how everything fits together.
""")
