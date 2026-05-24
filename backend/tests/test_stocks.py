from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_stocks() -> None:
    response = client.get("/api/v1/stocks")

    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_get_stock_by_ticker() -> None:
    response = client.get("/api/v1/stocks/NVDA")

    assert response.status_code == 200
    assert response.json()["ticker"] == "NVDA"


def test_get_unknown_stock() -> None:
    response = client.get("/api/v1/stocks/NOPE")

    assert response.status_code == 404
