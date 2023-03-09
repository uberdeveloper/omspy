from typing import Union, Optional
from pydantic import BaseModel
from fastapi import FastAPI
from omspy.simulation.virtual import VirtualBroker, FakeBroker
from omspy.simulation.models import VOrder, OrderResponse, Side, Status

app = FastAPI()
app.broker: FakeBroker = FakeBroker()


class OrderArgs(BaseModel):
    symbol: str
    side: Side
    quantity: Optional[int]
    price: Optional[float]
    trigger_price: Optional[float]
    s: Optional[Status]


class ModifyArgs(BaseModel):
    quantity: Optional[float]
    price: Optional[float]
    trigger_price: Optional[float]


@app.get("/")
def read_root():
    return {"hello": f"Welcome"}


@app.post("/order")
async def create_order(order: OrderArgs) -> OrderResponse:
    response = app.broker.order_place(**order.dict(exclude_none=True))

    return OrderResponse(status="success", data=response)


@app.put("/order/{order_id}")
async def modify_order(order_id: str, order: ModifyArgs) -> OrderResponse:
    response = app.broker.order_modify(order_id, **order.dict())
    return response


@app.delete("/order/{order_id}")
async def cancel_order(order_id: str) -> OrderResponse:
    order = app.broker.order_cancel(order_id=order_id)
    response = OrderResponse(status="success", data=order)
    return response
