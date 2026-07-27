from rook.app import RookApp
from rook.paths import default_database_path
from rook.persistence.database import connect
from rook.persistence.migrations import UnsupportedSchemaVersionError, migrate
from rook.persistence.tasks import TaskRepository
from rook.services.tasks import TaskService


def main() -> int:
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
    try:
        RookApp(task_service=task_service).run()
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
