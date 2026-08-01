# Rook ♖

A local, keyboard-first terminal journal for working through one day at a time.

```text
rook ♖  Today — Friday, July 24, 2026
⋆⁺₊ (｡'▽'｡)♡ ₊⁺⋆  "Showing up is the whole trick."

❯ • Finish the presentation
  • Reply to Alex
  > Read Chapter 3
  × Submit the expense report

[n] new   [e/Ent] edit   [x] complete   [>] migrate   [d] delete   [u] undo   [a] archive   [q] quit
```

Rook is inspired by the simplicity of a paper bullet journal:

- one active list: **Today**
- direct, in-place editing
- local SQLite storage
- read-only history
- no accounts, cloud sync, reminders, priorities, or telemetry

## Installation

Requires Python 3.10 or newer. Install with [uv](https://docs.astral.sh/uv/):

```powershell
uv tool install rook-cli
```

Then launch:

```powershell
rook
```

To upgrade later:

```powershell
uv tool upgrade rook-cli
```

## CLI reference

| Flag | Description |
|------|-------------|
| `rook` | Launch the app |
| `rook --version` | Print the installed version and exit |
| `rook --data-path` | Print the path to the database file and exit |
| `rook --week-start monday\|sunday` | Set which day the archive week starts on |
| `rook --reset` | Delete all data and start fresh (asks for confirmation) |

## Keyboard reference

| Key | Action |
|-----|--------|
| `n` | New task |
| `e` or `Ent` | Edit selected task |
| `x` | Toggle complete |
| `>` | Toggle migrated |
| `d` | Soft-delete (shows `~` and strikethrough) / permanently remove (press twice) |
| `u` | Undo last action |
| `a` | Open weekly archive |
| `↑` / `↓` | Move selection |
| `Esc` | Cancel edit |
| `q` | Quit |

> **Mac note:** strikethrough on soft-deleted tasks requires a terminal that supports it. macOS Terminal.app does not; [iTerm2](https://iterm2.com), Alacritty, and kitty do. The `~` bullet still appears regardless of terminal.

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

## FAQ

**How do I change the archive week layout from Sun–Sat to Mon–Sun?**

```powershell
rook --week-start monday
```

To switch back to Sunday-start:

```powershell
rook --week-start sunday
```

## License

Copyright (c) 2026 Janvi Chawla. All Rights Reserved.

Personal use permitted. No redistribution or derivative works without permission.
