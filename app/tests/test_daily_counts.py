import importlib
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

main = importlib.import_module("app.main")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_NAME", str(tmp_path / "daily.db"))
    main.setup_database()
    with TestClient(main.app) as client:
        yield client


def test_daily_counts_and_utc_dates(client, monkeypatch):
    code = client.post(
        "/shorten",
        json={"original_url": "https://example.com"},
    ).json()["short_code"]

    assert client.get(
        f"/analytics/{code}"
    ).json()["daily_counts"] == []

    for day in ["2026-09-06", "2026-09-05", "2026-09-06"]:
        monkeypatch.setattr(main, "utc_today", lambda day=day: day)
        response = client.get(f"/{code}", follow_redirects=False)
        assert response.status_code == 307

    data = client.get(f"/analytics/{code}").json()
    assert data["clicks"] == 3
    assert data["daily_counts"] == [
        {"date": "2026-09-05", "count": 1},
        {"date": "2026-09-06", "count": 2},
    ]


def test_preserves_existing_lifetime_clicks(client, monkeypatch):
    with closing(main.get_db()) as conn, conn:
        conn.execute(
            """INSERT INTO urls
               (short_code, original_url, clicks, created_at)
               VALUES (?, ?, ?, ?)""",
            ("legacy", "https://example.com", 10, "2026-09-01"),
        )

    before = client.get("/analytics/legacy").json()
    assert before["clicks"] == 10
    assert before["daily_counts"] == []

    monkeypatch.setattr(main, "utc_today", lambda: "2026-09-05")
    response = client.get("/legacy", follow_redirects=False)
    assert response.status_code == 307

    after = client.get("/analytics/legacy").json()
    assert after["clicks"] == 11
    assert after["daily_counts"] == [
        {"date": "2026-09-05", "count": 1}
    ]

def test_failed_daily_update_rolls_back_lifetime(client):
    code = client.post(
        "/shorten",
        json={"original_url": "https://example.com"},
    ).json()["short_code"]

    # Force the daily insert to fail after the lifetime update.
    with closing(main.get_db()) as conn, conn:
        conn.execute("""
            CREATE TRIGGER fail_daily_insert
            BEFORE INSERT ON daily_clicks
            BEGIN
                SELECT RAISE(ABORT, 'simulated daily failure');
            END;
        """)

    with TestClient(main.app, raise_server_exceptions=False) as failing_client:
        response = failing_client.get(
            f"/{code}", follow_redirects=False
        )

    assert response.status_code == 500

    data = client.get(f"/analytics/{code}").json()
    assert data["clicks"] == 0
    assert data["daily_counts"] == []


def test_concurrent_clicks(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    code = client.post(
        "/shorten",
        json={"original_url": "https://example.com"},
    ).json()["short_code"]

    monkeypatch.setattr(main, "utc_today", lambda: "2026-09-05")

    def click(_):
        # Each worker opens its own database connection.
        return main.redirect_to_original_url(code).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(click, range(20)))

    assert statuses == [307] * 20


    data = client.get(f"/analytics/{code}").json()
    assert data["clicks"] == 20
    assert data["daily_counts"] == [
        {"date": "2026-09-05", "count": 20}
    ]

def test_unknown_link_creates_no_daily_records(client):
    response = client.get(
        "/missing-code", follow_redirects=False
    )
    assert response.status_code == 404

    response = client.get("/analytics/missing-code")
    assert response.status_code == 404

    with closing(main.get_db()) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM daily_clicks"
        ).fetchone()[0]

    assert count == 0

def test_lock_timeout_returns_503(client, monkeypatch):
    import sqlite3

    code = client.post(
        "/shorten",
        json={"original_url": "https://example.com"},
    ).json()["short_code"]

    def short_wait_connection():
        conn = sqlite3.connect(main.DB_NAME, timeout=0.1)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    monkeypatch.setattr(main, "get_db", short_wait_connection)

    with closing(sqlite3.connect(main.DB_NAME)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        try:
            response = client.get(
                f"/{code}", follow_redirects=False
            )
            assert response.status_code == 503
            assert "location" not in response.headers
        finally:
            lock.rollback()

    data = client.get(f"/analytics/{code}").json()
    assert data["clicks"] == 0
    assert data["daily_counts"] == []


def test_schema_upgrade_preserves_old_links(tmp_path, monkeypatch):
    import sqlite3

    database = tmp_path / "old_database.db"
    monkeypatch.setattr(main, "DB_NAME", str(database))

    # Recreate the original schema, without daily_clicks.
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("""
            CREATE TABLE urls (
                short_code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO urls VALUES (?, ?, ?, ?)",
            ("old-link", "https://example.com", 12, "2026-09-01"),
        )

    # Running setup twice must be safe.
    main.setup_database()
    main.setup_database()

    with TestClient(main.app) as local_client:
        response = local_client.get("/analytics/old-link")

    assert response.status_code == 200
    assert response.json()["clicks"] == 12
    assert response.json()["daily_counts"] == []


def test_real_utc_helper_across_midnight(client, monkeypatch):
    from datetime import datetime, timezone

    code = client.post(
        "/shorten",
        json={"original_url": "https://example.com"},
    ).json()["short_code"]

    class FixedClock:
        current = datetime(
            2026, 9, 5, 23, 59, 59, tzinfo=timezone.utc
        )

        @classmethod
        def now(cls, tz=None):
            assert tz == timezone.utc
            return cls.current

    # Keep the real utc_today() helper; replace only its clock.
    monkeypatch.setattr(main, "datetime", FixedClock)

    assert client.get(
        f"/{code}", follow_redirects=False
    ).status_code == 307

    FixedClock.current = datetime(
        2026, 9, 6, 0, 0, 0, tzinfo=timezone.utc
    )

    assert client.get(
        f"/{code}", follow_redirects=False
    ).status_code == 307

    data = client.get(f"/analytics/{code}").json()
    assert data["clicks"] == 2
    assert data["daily_counts"] == [
        {"date": "2026-09-05", "count": 1},
        {"date": "2026-09-06", "count": 1},
    ]