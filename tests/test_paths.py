from pathlib import Path

from rook.paths import DATABASE_FILENAME, default_data_directory, default_database_path


def test_windows_data_directory_uses_localappdata(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\test\AppData\Local")

    assert default_data_directory() == Path(r"C:\Users\test\AppData\Local") / "Rook"


def test_database_path_is_never_in_the_repository_or_cwd(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    path = default_database_path()
    assert path.name == DATABASE_FILENAME
    assert path.parent == tmp_path / "Rook"
    assert Path.cwd() not in path.parents
