from fastapi.testclient import TestClient

from app.main import app
import importlib
import pytest

main_module = importlib.import_module("app.main")


@pytest.fixture(autouse=True)
def separate_test_database(tmp_path, monkeypatch):
    monkeypatch.setattr(
        main_module, "DB_NAME", str(tmp_path / "test_urls.db")
    )
    main_module.setup_database()

client = TestClient(app)


def test_create_short_url():
    response = client.post(
        "/shorten",
        json={"original_url": "https://www.example.com"}
    )

    assert response.status_code == 200
    body = response.json()
    assert "short_code" in body
    assert "short_url" in body


def test_reject_invalid_url():
    response = client.post(
        "/shorten",
        json={"original_url": "not-a-real-url"}
    )

    assert response.status_code == 400


def test_analytics_for_created_url():
    created = client.post(
        "/shorten",
        json={"original_url": "https://www.example.com"}
    ).json()

    short_code = created["short_code"]

    response = client.get(f"/analytics/{short_code}")

    assert response.status_code == 200
    assert response.json()["clicks"] == 0

def test_redirect_increases_click_count():
    created = client.post(
        "/shorten",
        json={"original_url": "https://www.example.com"}
    ).json()
    code = created["short_code"]

    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://www.example.com"

    analytics = client.get(f"/analytics/{code}")
    assert analytics.status_code == 200
    assert analytics.json()["clicks"] == 1