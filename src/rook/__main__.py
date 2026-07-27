import sys

from rook import __version__
from rook.app import RookApp
from rook.paths import default_database_path
from rook.persistence.database import connect
from rook.persistence.metadata import MetadataRepository
from rook.persistence.migrations import UnsupportedSchemaVersionError, migrate
from rook.persistence.tasks import TaskRepository
from rook.services.rollover import RolloverService
from rook.services.tasks import TaskService


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] == "--version":
            print(__version__)
            return 0
        if sys.argv[1] == "--data-path":
            print(default_database_path())
            return 0

    db_path = default_database_path()
    connection = connect(db_path)

    try:
        migrate(connection)
    except UnsupportedSchemaVersionError as error:
        connection.close()
        print(error)
        print(f"Database file: {db_path}")
        return 1

    task_service = TaskService(TaskRepository(connection))
    rollover_service = RolloverService(connection, MetadataRepository(connection))

    # Section 16.8: rollover runs once at startup, before Today ever renders.
    rollover_service.roll_forward_if_needed()

    try:
        RookApp(
            task_service=task_service,
            rollover_service=rollover_service,
            connection=connection,
        ).run()
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
