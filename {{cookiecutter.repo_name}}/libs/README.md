# Templates

This directory is intended for storing custom [Cookiecutter](https://cookiecutter.readthedocs.io/) templates that you can use with the MLWorkbench project.

## What is Cookiecutter?

Cookiecutter is a command-line utility that creates projects from project templates. It uses a templating language to replace variables in the template with user-provided values.

## How to use

1. **Create your custom Cookiecutter template**. Follow the [official documentation](https://cookiecutter.readthedocs.io/en/stable/index.html) to learn how to create a template. At minimum, your template should contain a `cookiecutter.json` file and a template directory.

2. **Save your template in the `templates` directory**. Each template should be in a separate directory within `templates`.

3. **Run Cookiecutter with your custom template**. Specify the path to your template in the `templates` directory. For example, if your template is in a directory named `my_template` within `templates`, you would run:

```bash
> cookiecutter lib/templates/my_template -o [destination directory]
```
