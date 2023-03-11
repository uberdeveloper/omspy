from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from omspy.simulation.virtual import FakeBroker
from omspy.simulation.models import (
    OrderResponse,
    Side,
    Status,
    AuthResponse,
    LTPResponse,
    OHLCVResponse,
    QuoteResponse,
    OrderBookResponse,
    PositionResponse,
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


@app.get("/")
def read_root():
    return {"hello": "Welcome"}


@app.post(
    "/order",
    summary="Create an order",
    description="Create an order with the given arguments",
)
async def create_order(order: OrderArgs) -> OrderResponse:
    if app._type == FakeBroker:
        response = app.broker.order_place(**order.dict(exclude_none=True))
    return OrderResponse(status="success", data=response)


@app.put(
    "/order/{order_id}",
    summary="Modify an order",
    description="Modify a existing order with the given order_id",
)
async def modify_order(order_id: str, order: OrderArgs) -> OrderResponse:
    if app._type == FakeBroker:
        response = app.broker.order_modify(
            order_id=order_id, **order.dict(exclude_none=True)
        )
    return OrderResponse(status="success", data=response)


@app.delete(
    "/order/{order_id}",
    summary="Delete order",
    description="Delete a existing order with the given order_id",
)
async def cancel_order(order_id: str, order: OrderArgs) -> OrderResponse:
    if app._type == FakeBroker:
        response = app.broker.order_cancel(
            order_id=order_id, **order.dict(exclude_none=True)
        )
    return OrderResponse(status="success", data=response)


@app.post(
    "/auth/{user_id}",
    summary="Authenticate the user",
    description="Authenticate the user",
)
async def auth(user_id: str) -> AuthResponse:
    return AuthResponse(status="success", user_id=user_id)


@app.get("/ltp/{symbol}", summary="Get the last price for the given symbol")
async def ltp(symbol: str) -> LTPResponse:
    response = app.broker.ltp(symbol)
    return LTPResponse(status="success", data=response)


@app.get(
    "/ohlc/{symbol}", summary="Get the ohlc prices and volume for the given symbol"
)
async def ohlc(symbol: str) -> OHLCVResponse:
    response = app.broker.ohlc(symbol)
    return OHLCVResponse(status="success", data=response)


@app.get(
    "/quote/{symbol}",
    summary="Get the detailed quote for the symbol",
    description="Quote contains OHLC, volume, last_price and the orderbook",
)
async def quote(symbol: str) -> QuoteResponse:
    response = app.broker.quote(symbol)
    return QuoteResponse(status="success", data=response)


@app.get("/orderbook/{symbol}", summary="Get the orderbook for the given symbol")
async def orderbook(symbol: str) -> OrderBookResponse:
    response = app.broker.orderbook(symbol)
    return OrderBookResponse(status="success", data=response)


@app.get("/positions", summary="Get random positions")
async def positions() -> PositionResponse:
    response = app.broker.positions()
    return PositionResponse(status="success", data=response)
