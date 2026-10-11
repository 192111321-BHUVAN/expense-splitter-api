import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    """A test client that uses a throwaway in-memory database."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def login_as(client, username):
    """Register the user (if needed) and return auth headers."""
    client.post("/auth/register", json={"username": username, "password": "secret123"})
    response = client.post(
        "/auth/login", data={"username": username, "password": "secret123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_trip(client):
    """alice, bob, charlie in one group. alice pays 3000, bob pays 900."""
    alice = login_as(client, "alice")
    bob = login_as(client, "bob")
    charlie = login_as(client, "charlie")

    group = client.post("/groups/", json={"name": "Goa Trip"}, headers=alice).json()
    for name in ("bob", "charlie"):
        r = client.post(f"/groups/{group['id']}/members", json={"username": name}, headers=alice)
        assert r.status_code == 200

    r = client.post(
        f"/groups/{group['id']}/expenses",
        json={"description": "Hotel", "amount": 3000},
        headers=alice,
    )
    assert r.status_code == 201
    r = client.post(
        f"/groups/{group['id']}/expenses",
        json={"description": "Dinner", "amount": 900},
        headers=bob,
    )
    assert r.status_code == 201
    return group["id"], alice, bob, charlie


def test_trip_balances_and_settlement(client):
    group_id, alice, _, _ = build_trip(client)

    balances = client.get(f"/groups/{group_id}/balances", headers=alice).json()
    by_name = {b["username"]: b["balance"] for b in balances}
    assert by_name == {"alice": 1700.0, "bob": -400.0, "charlie": -1300.0}

    payments = client.get(f"/groups/{group_id}/settle", headers=alice).json()
    assert sorted((p["payer"], p["receiver"], p["amount"]) for p in payments) == [
        ("bob", "alice", 400.0),
        ("charlie", "alice", 1300.0),
    ]


def test_uneven_amount_still_adds_up(client):
    alice = login_as(client, "alice")
    login_as(client, "bob")
    login_as(client, "charlie")
    group = client.post("/groups/", json={"name": "Lunch"}, headers=alice).json()
    for name in ("bob", "charlie"):
        client.post(f"/groups/{group['id']}/members", json={"username": name}, headers=alice)

    r = client.post(
        f"/groups/{group['id']}/expenses",
        json={"description": "Snacks", "amount": 1.00},
        headers=alice,
    )
    shares = sorted(s["share"] for s in r.json()["splits"])
    assert shares == [0.33, 0.33, 0.34]
    assert round(sum(shares), 2) == 1.00


def test_split_among_selected_members(client):
    group_id, alice, _, _ = build_trip(client)
    r = client.post(
        f"/groups/{group_id}/expenses",
        json={"description": "Taxi", "amount": 200, "split_among": ["alice", "bob"]},
        headers=alice,
    )
    assert r.status_code == 201
    assert {s["username"] for s in r.json()["splits"]} == {"alice", "bob"}


def test_cannot_delete_someone_elses_expense(client):
    group_id, _, _, charlie = build_trip(client)
    r = client.delete(f"/groups/{group_id}/expenses/1", headers=charlie)
    assert r.status_code == 403


def test_owner_can_delete_own_expense(client):
    group_id, alice, _, _ = build_trip(client)
    assert client.delete(f"/groups/{group_id}/expenses/1", headers=alice).status_code == 204
    expenses = client.get(f"/groups/{group_id}/expenses", headers=alice).json()
    assert [e["description"] for e in expenses] == ["Dinner"]


def test_requires_login(client):
    assert client.get("/groups/").status_code == 401


def test_non_member_is_blocked(client):
    group_id, _, _, _ = build_trip(client)
    stranger = login_as(client, "stranger")
    assert client.get(f"/groups/{group_id}/balances", headers=stranger).status_code == 403


def test_split_among_user_not_in_group_is_rejected(client):
    group_id, alice, _, _ = build_trip(client)
    login_as(client, "stranger")
    r = client.post(
        f"/groups/{group_id}/expenses",
        json={"description": "Gift", "amount": 100, "split_among": ["alice", "stranger"]},
        headers=alice,
    )
    assert r.status_code == 400


def test_duplicate_username_rejected(client):
    login_as(client, "alice")
    r = client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 400


def test_wrong_password_rejected(client):
    login_as(client, "alice")
    r = client.post("/auth/login", data={"username": "alice", "password": "wrongpass"})
    assert r.status_code == 401
