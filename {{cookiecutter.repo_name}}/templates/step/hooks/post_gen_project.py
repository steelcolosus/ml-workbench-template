"""Print what to add to main.py and config.yaml for the new step."""

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

if PARAMETERS:
    section = "\n".join(f"    {p}:" for p in PARAMETERS)
    print(f"2. Add its section to config.yaml (with the values):\n\n{STEP}:\n{section}\n")
    print(
        f"Then set the parameter types and descriptions in src/steps/{STEP}/MLproject"
        " and run.py, and implement run()."
    )
else:
    print(f"Then implement run() in src/steps/{STEP}/run.py.")
