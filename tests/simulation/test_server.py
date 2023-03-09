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
