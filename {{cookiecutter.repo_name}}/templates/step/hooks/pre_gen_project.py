"""Stop before generating a step whose name or parameters aren't valid Python names."""

import re
import sys

STEP_NAME = {{ cookiecutter.step_name | tojson }}
PARAMETERS = {{ cookiecutter.parameters | tojson }}
SNAKE_CASE = re.compile(r"^[a-z_][a-z0-9_]*$")

errors = []
if not SNAKE_CASE.match(STEP_NAME):
    errors.append(
        f"step_name {STEP_NAME!r} must be snake_case (lowercase letters, digits "
        "and _), e.g. data_check: it names the folder, the config section and "
        "the step's class"
    )
for name in (p.strip() for p in PARAMETERS.split(",")):
    if name and not SNAKE_CASE.match(name):
        errors.append(f"parameter {name!r} must be snake_case, e.g. input_artifact")

if errors:
    print("\n".join(f"ERROR: {error}" for error in errors))
    sys.exit(1)
