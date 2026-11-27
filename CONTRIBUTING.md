# Contributing to CEREBRO

## Local setup

Use Python 3.10 or later with SQLite support. From the repository root, create and activate a virtual environment, then install the project and its test dependencies.

```sh
python -m venv .venv
# macOS or Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the tests

```sh
python -m pytest -q
```

Add or update tests for changes in behavior. Use synthetic records in examples and test fixtures.

## Pull requests

Open a pull request against `main` from your working branch or fork. Use a descriptive title and include a short summary of what changed, why it changed, and how you tested it. Link the relevant issue if there is one.
