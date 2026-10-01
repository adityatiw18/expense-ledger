from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

import uuid


client = TestClient(app)


def test_create_user_api():
    email = f"api-test-{uuid.uuid4()}@example.com"

    response = client.post(
        "/users",
        json={
            "name": "API Test User",
            "email": email
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "API Test User"
    assert data["email"] == email
    assert "id" in data


def test_duplicate_user_email():
    client.post(
        "/users",
        json={
            "name": "Duplicate Test",
            "email": "duplicate-test@example.com"
        }
    )

    response = client.post(
        "/users",
        json={
            "name": "Duplicate Test 2",
            "email": "duplicate-test@example.com"
        }
    )

    assert response.status_code == 400


def test_create_group_api(test_data):
    response = client.post(
        "/groups",
        json={
            "name": "API Test Group",
            "created_by": test_data["user1"]
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "API Test Group"
    assert data["created_by"] == test_data["user1"]


def test_create_group_invalid_user():
    response = client.post(
        "/groups",
        json={
            "name": "Invalid Group",
            "created_by": 999999
        }
    )

    assert response.status_code == 404


def test_add_member_api(test_data):
    email = f"fourth-user-{uuid.uuid4()}@example.com"

    user_response = client.post(
        "/users",
        json={
            "name": "Fourth User",
            "email": email
        }
    )

    assert user_response.status_code == 201

    user_id = user_response.json()["id"]

    response = client.post(
        f"/groups/{test_data['group_id']}/members",
        json={
            "user_id": user_id
        }
    )

    assert response.status_code == 201


def test_add_nonexistent_user(test_data):
    response = client.post(
        f"/groups/{test_data['group_id']}/members",
        json={
            "user_id": 999999
        }
    )

    assert response.status_code == 404


def test_add_member_to_nonexistent_group():
    response = client.post(
        "/groups/999999/members",
        json={
            "user_id": 1
        }
    )

    assert response.status_code == 404


def test_duplicate_member(test_data):
    response = client.post(
        f"/groups/{test_data['group_id']}/members",
        json={
            "user_id": test_data["user1"]
        }
    )

    assert response.status_code == 400


def test_get_group_api(test_data):
    response = client.get(
        f"/groups/{test_data['group_id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_data["group_id"]
    assert data["name"] == "PYTEST - Expense Ledger"


def test_get_nonexistent_group():
    response = client.get(
        "/groups/999999"
    )

    assert response.status_code == 404


def test_create_expense_api(test_data):
    response = client.post(
        f"/groups/{test_data['group_id']}/expenses",
        json={
            "description": "Hotel",
            "created_by": test_data["user1"],
            "paid_by": test_data["user1"],
            "splits": {
                str(test_data["user1"]): "400.00",
                str(test_data["user2"]): "300.00",
                str(test_data["user3"]): "300.00"
            }
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert "transaction_id" in data
    assert data["description"] == "Hotel"


def test_invalid_expense_api(test_data):
    response = client.post(
        f"/groups/{test_data['group_id']}/expenses",
        json={
            "description": "Invalid Expense",
            "created_by": test_data["user1"],
            "paid_by": test_data["user1"],
            "splits": {
                str(test_data["user1"]): "-100.00",
                str(test_data["user2"]): "200.00"
            }
        }
    )

    assert response.status_code == 400


def test_get_balances_api(test_data):
    response = client.post(
        f"/groups/{test_data['group_id']}/expenses",
        json={
            "description": "Dinner",
            "created_by": test_data["user1"],
            "paid_by": test_data["user1"],
            "splits": {
                str(test_data["user1"]): "100.00",
                str(test_data["user2"]): "100.00",
                str(test_data["user3"]): "100.00"
            }
        }
    )

    assert response.status_code == 201

    response = client.get(
        f"/groups/{test_data['group_id']}/balances"
    )

    assert response.status_code == 200

    data = response.json()

    assert Decimal(data[str(test_data["user1"])]) == Decimal("200.00")
    assert Decimal(data[str(test_data["user2"])]) == Decimal("-100.00")
    assert Decimal(data[str(test_data["user3"])]) == Decimal("-100.00")


def test_get_settlements_api(test_data):
    response = client.post(
        f"/groups/{test_data['group_id']}/expenses",
        json={
            "description": "Dinner",
            "created_by": test_data["user1"],
            "paid_by": test_data["user1"],
            "splits": {
                str(test_data["user1"]): "100.00",
                str(test_data["user2"]): "100.00",
                str(test_data["user3"]): "100.00"
            }
        }
    )

    assert response.status_code == 201

    response = client.get(
        f"/groups/{test_data['group_id']}/settlements"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    total = sum(
        Decimal(item["amount"])
        for item in data
    )

    assert total == Decimal("200.00")