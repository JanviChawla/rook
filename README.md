# Rook ♖

A local, keyboard-first terminal journal for working through one day at a time.

```text
rook ♖  Today — Friday, July 24, 2026
⋆⁺₊ (｡'▽'｡)♡ ₊⁺⋆  "Showing up is the whole trick."

❯ • Finish the presentation
  • Reply to Alex
  > Read Chapter 3
  × Submit the expense report

[n] new   [e] edit   [x] complete   [>] migrate   [d] delete   [u] undo   [a] archive   [q] quit
```

Rook is inspired by the simplicity of a paper bullet journal:

- one active list: **Today**
- direct, in-place editing
- local SQLite storage
- read-only history
- no accounts, cloud sync, reminders, priorities, or telemetry

## Installation

Requires Python 3.10 or newer. Install with [pipx](https://pipx.pypa.io) for an isolated environment:

```powershell
pipx install git+https://github.com/JanviChawla/rook.git
```

Then launch:

```powershell
rook
```

To upgrade later:

```powershell
pipx upgrade rook
```

## Keyboard reference

| Key | Action |
|-----|--------|
| `n` | New task |
| `e` or `Enter` | Edit selected task |
| `x` | Toggle complete |
| `>` | Toggle migrated |
| `d` | Soft-delete / permanently remove (press twice) |
| `u` | Undo last action |
| `a` | Open weekly archive |
| `↑` / `↓` | Move selection |
| `Esc` | Cancel edit |
| `q` | Quit |

## Data and privacy

Tasks are stored in a local SQLite database. Nothing leaves your machine.

| Platform | Location |
|----------|----------|
| Windows  | `%LOCALAPPDATA%\Rook\data.sqlite3` |
| macOS    | `~/Library/Application Support/Rook/data.sqlite3` |
| Linux    | `~/.local/share/rook/data.sqlite3` |

To print the exact path on your system:

```powershell
rook --data-path
```

Uninstalling Rook does not delete the database.

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

## FAQ

**How do I change the archive week layout from Sun–Sat to Mon–Sun?**

There is no in-app setting yet. Update the value directly in the SQLite database.
Find the exact path with `rook --data-path`, or use the default:

```powershell
sqlite3 "$env:LOCALAPPDATA\Rook\data.sqlite3"
```

```sql
INSERT OR REPLACE INTO app_meta (key, value) VALUES ('week_start_day', 'monday');
```

To switch back to Sunday-start:

```sql
INSERT OR REPLACE INTO app_meta (key, value) VALUES ('week_start_day', 'sunday');
```

## License

MIT
