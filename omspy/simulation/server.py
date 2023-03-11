from typing import Union, Optional, Dict
from pydantic import BaseModel
from fastapi import FastAPI
from omspy.simulation.virtual import VirtualBroker, FakeBroker
from omspy.simulation.models import (
    VOrder,
    OrderResponse,
    Side,
    Status,
    AuthResponse,
    GenericResponse,
    VQuote,
    VPosition,
    LTPResponse,
)

app = FastAPI()
app.broker: FakeBroker = FakeBroker()
app._type = type(app.broker)


class OrderArgs(BaseModel):
    symbol: Optional[str]
    side: Optional[Side]
    quantity: Optional[int]
    price: Optional[float]
    trigger_price: Optional[float]
    s: Optional[Status]


class CreateArgs(BaseModel):
    symbol: str
    side: Side
    quantity: Optional[int]
    price: Optional[float]
    trigger_price: Optional[float]


class ModifyArgs(BaseModel):
    quantity: Optional[float]
    price: Optional[float]
    trigger_price: Optional[float]


class QuoteResponse(GenericResponse):
    data: Dict[str, VQuote]


@app.get("/")
def read_root():
    return {"hello": f"Welcome"}


@app.post("/order")
async def create_order(order: OrderArgs) -> OrderResponse:
    if app._type == FakeBroker:
        response = app.broker.order_place(**order.dict(exclude_none=True))
    return OrderResponse(status="success", data=response)


@app.put("/order/{order_id}")
async def modify_order(order_id: str, order: OrderArgs) -> OrderResponse:
    if app._type == FakeBroker:
        response = app.broker.order_modify(
            order_id=order_id, **order.dict(exclude_none=True)
        )
    return OrderResponse(status="success", data=response)


@app.delete("/order/{order_id}")
async def cancel_order(order_id: str, order: OrderArgs) -> OrderResponse:
    if app._type == FakeBroker:
        response = app.broker.order_cancel(
            order_id=order_id, **order.dict(exclude_none=True)
        )
    return OrderResponse(status="success", data=response)


@app.post("/auth/{user_id}")
async def auth(user_id: str) -> AuthResponse:
    return AuthResponse(status="success", user_id=user_id)


@app.get("/ltp/{symbol}")
async def ltp(symbol: str) -> LTPResponse:
    response = app.broker.ltp(symbol)
    return LTPResponse(status="success", data=response)
