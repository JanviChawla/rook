import pytest

from rook.domain.tasks import TaskState
from rook.symbols import PREFERRED, SAFE, state_symbol


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (TaskState.OPEN, "•"),
        (TaskState.MIGRATED, ">"),
        (TaskState.COMPLETED, "×"),
        (TaskState.DELETED, "•"),
    ],
)
def test_preferred_symbols(state: TaskState, expected: str) -> None:
    assert state_symbol(state, PREFERRED, safe_mode=False) == expected


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (TaskState.OPEN, "*"),
        (TaskState.MIGRATED, ">"),
        (TaskState.COMPLETED, "x"),
        (TaskState.DELETED, "~"),
    ],
)
def test_safe_symbols(state: TaskState, expected: str) -> None:
    assert state_symbol(state, SAFE, safe_mode=True) == expected
