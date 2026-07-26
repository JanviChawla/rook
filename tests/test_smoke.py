from rook import __version__
from rook.__main__ import main


def test_package_exposes_version() -> None:
    assert __version__


def test_main_runs_without_error() -> None:
    exit_code = main()
    assert exit_code == 0
