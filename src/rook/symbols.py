from dataclasses import dataclass

from rook.domain.tasks import TaskState

# Column layout is fixed (Section 11.3): selection indicator, space, state
# symbol, space, then task text. The reserved selection column plus its
# following space is 2 characters; the state symbol plus its following
# space is another 2 characters.
PREFIX_WIDTH = 4


@dataclass(frozen=True, slots=True)
class SymbolSet:
    open: str
    completed: str
    migrated: str
    selected: str
    deleted_fallback: str


PREFERRED = SymbolSet(open="•", completed="×", migrated=">", selected="❯", deleted_fallback="~")
SAFE = SymbolSet(open="*", completed="x", migrated=">", selected=">", deleted_fallback="~")


def state_symbol(state: TaskState, symbols: SymbolSet, *, safe_mode: bool) -> str:
    """The glyph shown in the state-symbol column for a given Task state.

    A Deleted Task always shows the ``deleted_fallback`` symbol (``~``);
    in preferred mode the text is also struck through (Section 11.5, 11.7).
    """
    if state is TaskState.DELETED:
        return symbols.deleted_fallback
    if state is TaskState.OPEN:
        return symbols.open
    if state is TaskState.MIGRATED:
        return symbols.migrated
    if state is TaskState.COMPLETED:
        return symbols.completed
    raise AssertionError(f"Unhandled task state: {state!r}")
