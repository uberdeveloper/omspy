from omspy.brokers.paper import Paper


def test_broker_paper_properties():
    broker = Paper()
    assert broker.orders == [{}]
    assert broker.positions == [{}]
    assert broker.trades == [{}]


def test_broker_load_defaults():
    broker = Paper(
        positions=[{"symbol": "aapl", "qty": 10}, {"symbol": "goog", "qty": -15}]
    )
    assert broker.positions == [
        {"symbol": "aapl", "quantity": 10},
        {"symbol": "goog", "quantity": -15},
    ]
