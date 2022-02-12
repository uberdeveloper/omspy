from omspy.multi import *
from omspy.brokers.paper import Paper
import pytest


class Paper2(Paper):
    pass

    def some_method(self):
        return 'method called'

@pytest.fixture
def users_simple():
    users = [
            User(broker=Paper()),
            User(broker=Paper(),scale=0.5,name='user2'),
            User(broker=Paper2(),scale=2)
            ]
    return users

def test_user_defaults():
    user = User(broker=Paper(),name='mine',
            scale=0.5)
    assert user.scale == 0.5
    assert user.name == 'mine'

def test_multi_broker_defaults(users_simple):
    multi = MultiBroker(users=users_simple)
    for user,expected in zip(multi.users,(1,0.5,2)):
        assert user.scale == expected
    multi.users[1].scale = 0.75
    assert multi.users[1].scale == 0.75

def test_multi_broker_add(users_simple):
    multi = MultiBroker(users=users_simple)
    multi.add(User(broker=Paper(), scale=1.5, name='added'))
    assert multi.users[-1].scale == 1.5
    assert multi.users[-1].name == 'added'
    assert multi.count == 4


