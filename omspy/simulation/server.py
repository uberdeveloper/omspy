from typing import Union, Optional
from pydantic import BaseModel
from fastapi import FastAPI
from omspy.simulation.virtual import VirtualBroker
from omspy.simulation.models import VOrder, OrderResponse, Side

app = FastAPI()
app.broker:VirtualBroker = VirtualBroker()

class OrderArgs(BaseModel):
    symbol: str
    side: Side
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]

@app.get("/")
def read_root():
    return {'hello': "Welcome"}


@app.post("/order")
async def create_order(order:OrderArgs)->OrderResponse:
    return app.broker.order_place(**order.dict())

