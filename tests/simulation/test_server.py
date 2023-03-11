from fastapi import FastAPI
from fastapi.testclient import TestClient
from omspy.simulation.server import app
import pytest
import random

client = TestClient(app)


def test_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"hello": "Welcome"}


def test_order_default():
    data = dict(symbol="amzn", side=1)
    response = client.post("/order", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["symbol"] == "amzn"
    assert r["quantity"] > 0
    assert r["side"] == 1
    assert r["quantity"] == r["filled_quantity"]


def test_order_more_args():
    data = dict(symbol="amzn", side=1, quantity=100, price=125)
    response = client.post("/order", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["symbol"] == "amzn"
    assert r["quantity"] == 100
    assert r["side"] == 1
    assert r["price"] == 125
    assert r["filled_quantity"] == 100


def test_order_status_canceled():
    data = dict(symbol="amzn", side=-1, quantity=100, s=2)
    response = client.post("/order", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["symbol"] == "amzn"
    assert r["side"] == -1
    assert r["quantity"] == 100
    assert r["filled_quantity"] == r["pending_quantity"] == 0
    assert r["canceled_quantity"] == 100


def test_order_status_open():
    data = dict(symbol="amzn", side=-1, quantity=100, s=5)
    response = client.post("/order", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["symbol"] == "amzn"
    assert r["side"] == -1
    assert r["quantity"] == 100
    assert r["filled_quantity"] == r["canceled_quantity"] == 0
    assert r["pending_quantity"] == 100


def test_order_modify():
    data = dict(price=120, quantity=125)
    response = client.put("/order/abcd1234", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["price"] == 120
    assert r["quantity"] == 125


def test_order_modify_other_args():
    data = dict(price=120, quantity=125, symbol="abcd", side=-1, s=2)
    response = client.put("/order/abcd1234", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["order_id"] == "abcd1234"
    assert r["symbol"] == "abcd"
    assert r["side"] == -1
    assert r["pending_quantity"] == 125
    assert r["canceled_quantity"] == r["filled_quantity"] == 0


def test_order_cancel():
    response = client.request(method="delete", url="/order/abcd1234", json=dict())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["order_id"] == "abcd1234"
    assert r["canceled_quantity"] == r["quantity"]


def test_order_cancel_other_args():
    data = dict(price=120, quantity=1000, symbol="abcd", side=-1, s=1)
    response = client.request(method="delete", url="/order/abcd1234", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    r = response.json()["data"]
    assert r["order_id"] == "abcd1234"
    assert r["symbol"] == "abcd"
    assert r["side"] == -1
    assert r["pending_quantity"] == r["filled_quantity"] == 0
    assert r["canceled_quantity"] == 1000


def test_auth():
    response = client.post("/auth/user_abcd")
    assert response.status_code == 200
    r = response.json()
    assert r["status"] == "success"
    assert r["user_id"] == "user_abcd"
    assert r["message"] == "Authentication successful"


def test_ltp():
    response = client.get("/ltp/aapl")
    assert response.status_code == 200
    r = response.json()["data"]
    assert r["aapl"] > 0
