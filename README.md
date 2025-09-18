# LangConnect CLI

A lightweight command-line interface to interact with the LangConnect API.

## Setup

1. Create and configure your environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Environment variables are expected in a `.env` file at the project root.

## Usage

Invoke the CLI via:

```bash
python -m langconnect_cli --help
```

Example commands:

- Sign in:
  ```bash
  python -m langconnect_cli signin
  ```
- Fetch data:
  ```bash
  python -m langconnect_cli get projects --param status=active
  ```
- Create via POST:
  ```bash
  python -m langconnect_cli post users --json '{"email": "user@example.com"}'
  ```
- Delete:
  ```bash
  python -m langconnect_cli delete users/123
  ```

Increase verbosity with `-v` (repeatable).
