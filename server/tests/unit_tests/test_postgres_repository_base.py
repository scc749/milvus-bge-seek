from agent.repositories.postgres_base import PostgresRepositoryBase


class _FakeConnection:
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0
        self.closed = 0

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def close(self) -> None:
        self.closed += 1


class _TestRepository(PostgresRepositoryBase):
    def __init__(self, connection: _FakeConnection | None) -> None:
        self._connection = connection
        super().__init__(schema_manager=None)

    def _connect_for_transaction(self):
        return self._connection


def test_transaction_commits_on_success() -> None:
    connection = _FakeConnection()
    repository = _TestRepository(connection)

    with repository._transaction() as conn:
        assert conn is connection

    assert connection.committed == 1
    assert connection.rolled_back == 0
    assert connection.closed == 1


def test_transaction_rolls_back_on_error() -> None:
    connection = _FakeConnection()
    repository = _TestRepository(connection)

    try:
        with repository._transaction():
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert connection.committed == 0
    assert connection.rolled_back == 1
    assert connection.closed == 1


def test_transaction_yields_none_when_connection_unavailable() -> None:
    repository = _TestRepository(None)

    with repository._transaction() as conn:
        assert conn is None
