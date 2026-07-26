# Rook ♖

A local, keyboard-first terminal journal for working through one day at a time.

```text
Rook ♖  Friday, July 24, 2026
( •̀ᴗ•́ )و  "Your next move."

❯ • Finish the presentation
  • Reply to Alex
  > Read Chapter 3
  × Submit the expense report

[n] new   [e] edit   [x] complete   [>] migrate   [d] delete   [u] undo   [r] routine   [a] archive   [?] help   [q] quit
```

Rook is inspired by the simplicity of a paper bullet journal:

- one active list: **Today**
- direct, in-place editing
- local SQLite storage
- read-only history
- reusable routines that stay out of the daily archive
- no accounts, cloud sync, reminders, priorities, or telemetry

> Early development. The interface and core architecture are defined; implementation is underway.

## Development setup

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Run the test suite:

```powershell
python -m pytest
```

Run formatting, lint, and type checks:

```powershell
python -m ruff format --check .
python -m ruff check .
python -m mypy src
```

Run the application during development:

```powershell
python -m rook
```

## License

MIT
