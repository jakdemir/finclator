from src import admin


def test_fixture_loads(conn):
    assert conn.execute("SELECT count(*) FROM tweets").fetchone()[0] == 4
    assert admin.status(conn)["calls"] == 2
