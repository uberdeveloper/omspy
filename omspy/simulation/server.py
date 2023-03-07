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

class ModifyArgs(BaseModel):
    quantity: Optional[float]
    price: Optional[float]
    trigger_price: Optional[float]

@app.get("/")
def read_root():
    return {'hello': f"Welcome - Number of orders is {len(app.broker._orders)}"}


@app.post("/order")
async def create_order(order:OrderArgs)->OrderResponse:
    response = app.broker.order_place(**order.dict())
    return response

@app.put("/order/{order_id}")
async def modify_order(order_id:str, order:ModifyArgs)->OrderResponse:
    response = app.broker.order_modify(order_id, **order.dict())
    return response


@app.delete("/order/{order_id}")
async def cancel_order(order_id:str)->OrderResponse:
    response = app.broker.order_cancel(order_id)
    return response

