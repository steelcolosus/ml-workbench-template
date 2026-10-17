"""
Move the step's test to tests/steps/ and print what to add to main.py and
config.yaml for the new step.
"""

from pathlib import Path

STEP = {{ cookiecutter.step_name | tojson }}
PARAMETERS = [
    p.strip()
    for p in {{ cookiecutter.parameters | tojson }}.split(",")
    if p.strip() and p.strip() != "config_path"
]

if PARAMETERS:
    arguments = "".join(
        f'\n                {p}=config["{STEP}"]["{p}"],' for p in PARAMETERS
    )
    call = f'runner.run(\n                "{STEP}",{arguments}\n            )'
else:
    call = f'runner.run("{STEP}")'

print(f"""
Step created in src/steps/{STEP}

1. Add "{STEP}" to _steps in main.py and run it inside the `with` block:

        if "{STEP}" in active_steps:
            {call}
""")

# The step is generated in <project>/src/steps/<step>: its test goes to
# <project>/tests/steps/test_<step>.py
generated_test = Path("_test_step.py")
project = Path.cwd().parents[2]
test_file = project / "tests" / "steps" / f"test_{STEP}.py"
if not (project / "config.yaml").is_file():
    test_note = f"The step's test is in {generated_test.resolve()}: move it to your tests."
elif test_file.exists():
    generated_test.unlink()
    test_note = f"{test_file.relative_to(project)} already exists and was kept."
else:
    test_file.parent.mkdir(parents=True, exist_ok=True)
    generated_test.rename(test_file)
    test_note = f"Its test is in {test_file.relative_to(project)} (skipped until you write it)."

if PARAMETERS:
    section = "\n".join(f"    {p}:" for p in PARAMETERS)
    print(f"2. Add its section to config.yaml (with the values):\n\n{STEP}:\n{section}\n")
    print(
        f"Then set the parameter types and descriptions in src/steps/{STEP}/MLproject"
        " and run.py, and implement run()."
    )
else:
    print(f"Then implement run() in src/steps/{STEP}/run.py.")
print(test_note)
