"""
Main tutorial file for demonstrating omspy.brokers.zerodha with FastAPI.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# Assuming omspy structure - these might need adjustment if omspy is structured differently
# It's common for broker-specific classes to be in a sub-module
# and core classes like Order in a more central place.
try:
    from omspy.brokers.zerodha import Zerodha
    from omspy.order import Order, OrderStatus # Assuming OrderStatus might be part of omspy.order
    # Enums for order types, products etc. might also be in omspy.order or omspy.enums
    # For now, we'll use strings and validate them in Pydantic models.
except ImportError:
    # This is a fallback/mock for environments where omspy isn't installed
    # or if the structure is different. This allows the FastAPI app to still be defined.
    print("Warning: omspy library not found or structure is different. Using mock objects.")

    class Zerodha:
        def __init__(self, userid, password, apikey, secret, pin):
            self.userid = userid
            print(f"MockBroker initialized for user {userid}. Connection successful (mocked).")

        def authenticate(self):
            print("Mock authentication successful.")
            return True # Mocked

        def order_place(self, order: Dict[str, Any]) -> Dict[str, Any]:
            print(f"Mock placing order: {order}")
            return {"order_id": "mock_order_123", "status": "PENDING", **order}

        def order_modify(self, order_id: str, **kwargs: Any) -> Dict[str, Any]:
            print(f"Mock modifying order {order_id} with {kwargs}")
            return {"order_id": order_id, "status": "MODIFIED", **kwargs}

        def order_cancel(self, order_id: str) -> Dict[str, Any]:
            print(f"Mock cancelling order {order_id}")
            return {"order_id": order_id, "status": "CANCELLED"}

        @property
        def orders(self) -> List[Dict[str, Any]]:
            print("Mock fetching all orders.")
            return [{"order_id": "mock_order_123", "symbol": "SBIN-EQ", "quantity": 1, "status": "COMPLETE"}]

        def get_order_history(self, order_id: str) -> List[Dict[str, Any]]: # Or get_order_status
             print(f"Mock fetching history for order {order_id}")
             return [{"order_id": order_id, "status": "COMPLETE", "message": "Mocked order details"}]


        @property
        def positions(self) -> List[Dict[str, Any]]:
            print("Mock fetching positions.")
            return [{"symbol": "RELIANCE-EQ", "quantity": 10, "pnl": 100.50}]

        @property
        def funds(self) -> Dict[str, Any]:
            print("Mock fetching funds.")
            return {"equity": {"available_margin": 10000, "used_margin": 500}}

        def quote(self, symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
            print(f"Mock fetching quote for {symbol} on {exchange or 'default_exchange'}")
            return {"symbol": symbol, "ltp": 2500.00, "ohlc": {"open": 2490, "high": 2510, "low": 2485, "close": 2500}}

    class Order: # Mock Order class
        def __init__(self, symbol: str, quantity: int, side: str, order_type: str,
                     product: str, exchange: str, price: Optional[float] = None,
                     trigger_price: Optional[float] = None, validity: Optional[str] = None,
                     disclosed_quantity: Optional[int] = None, tag: Optional[str] = None,
                     **kwargs):
            self.symbol = symbol
            self.quantity = quantity
            self.side = side # BUY or SELL
            self.order_type = order_type # MARKET, LIMIT, SL, SLM
            self.product = product # CNC, MIS, NRML
            self.exchange = exchange # NSE, BSE, NFO, MCX etc.
            self.price = price
            self.trigger_price = trigger_price
            self.validity = validity # DAY, IOC
            self.disclosed_quantity = disclosed_quantity
            self.tag = tag
            self.kwargs = kwargs # For any other params

        def to_dict(self) -> Dict[str, Any]:
            # Helper to convert to dict for broker methods if needed
            data = {
                "symbol": self.symbol,
                "quantity": self.quantity,
                "transaction_type": self.side, # Mapping 'side' to Zerodha's 'transaction_type'
                "order_type": self.order_type,
                "product": self.product,
                "exchange": self.exchange,
            }
            if self.price is not None: data["price"] = self.price
            if self.trigger_price is not None: data["trigger_price"] = self.trigger_price
            if self.validity is not None: data["validity"] = self.validity
            if self.disclosed_quantity is not None: data["disclosed_quantity"] = self.disclosed_quantity
            if self.tag is not None: data["tag"] = self.tag
            if self.kwargs: data.update(self.kwargs)
            return data

    class OrderStatus: # Mock
        COMPLETE = "COMPLETE"
        PENDING = "PENDING"
        CANCELLED = "CANCELLED"
        REJECTED = "REJECTED"
        OPEN = "OPEN"


# Initialize FastAPI app
app = FastAPI(
    title="omspy Zerodha Broker API Tutorial",
    description="A tutorial demonstrating how to interact with a Zerodha broker account using omspy and FastAPI.",
    version="0.1.0",
)

# --- Global Variables ---
# Placeholder for the broker instance.
# This will be initialized after successful authentication.
broker: Optional[Zerodha] = None
# Store credentials globally for simplicity in this tutorial.
# In a real app, manage these securely (e.g., env variables, config files, secrets manager).
CREDENTIALS: Dict[str, Optional[str]] = {
    "user_id": None,
    "password": None,
    "api_key": None,
    "api_secret": None,
    "pin": None,
}

# --- Pydantic Models for Request/Response bodies ---

class ConnectionRequest(BaseModel):
    user_id: str = Field(..., example="AB1234")
    password: str = Field(..., example="your_password")
    api_key: str = Field(..., example="your_api_key")
    api_secret: str = Field(..., example="your_api_secret")
    pin: str = Field(..., example="your_2fa_pin")

class ConnectionResponse(BaseModel):
    message: str
    user_id: Optional[str] = None

class OrderRequest(BaseModel):
    symbol: str = Field(..., example="SBIN-EQ", description="Trading symbol (e.g., INFY-EQ, NIFTY23JULFUT)")
    quantity: int = Field(..., gt=0, example=1, description="Order quantity")
    side: str = Field(..., example="BUY", description="Transaction type: BUY or SELL")
    order_type: str = Field(..., example="LIMIT", description="Order type: MARKET, LIMIT, SL, SL-M")
    product: str = Field(..., example="MIS", description="Product type: MIS, CNC, NRML")
    exchange: str = Field(..., example="NSE", description="Exchange: NSE, BSE, NFO, MCX, etc.")
    price: Optional[float] = Field(None, example=3000.50, description="Price for LIMIT or SL orders")
    trigger_price: Optional[float] = Field(None, example=2990.00, description="Trigger price for SL or SL-M orders")
    validity: Optional[str] = Field("DAY", example="DAY", description="Order validity: DAY, IOC")
    disclosed_quantity: Optional[int] = Field(None, example=10, description="Disclosed quantity for iceberg orders")
    tag: Optional[str] = Field(None, example="my_strategy_tag", description="Optional tag for the order")
    # We can add more specific fields or a generic kwargs field if omspy's Order supports it
    # extra_params: Optional[Dict[str, Any]] = Field(None, description="Any other broker-specific parameters")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "INFY-EQ",
                "quantity": 1,
                "side": "BUY",
                "order_type": "LIMIT",
                "product": "CNC",
                "exchange": "NSE",
                "price": 1300.00,
                "tag": "my_infy_investment"
            }
        }

class OrderResponse(BaseModel):
    order_id: Optional[str] = Field(None, example="230725000000001")
    status: str = Field(..., example="PENDING")
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ModifyOrderRequest(BaseModel):
    quantity: Optional[int] = Field(None, gt=0, example=2)
    price: Optional[float] = Field(None, example=3005.00)
    trigger_price: Optional[float] = Field(None, example=2995.00)
    order_type: Optional[str] = Field(None, example="LIMIT") # Be cautious, some brokers don't allow type modification

class GeneralResponse(BaseModel):
    message: str
    data: Optional[Any] = None


# --- Helper Functions (if any needed later) ---

# --- API Endpoints will be defined below ---

# --- Order Object and Attributes ---
# The following Pydantic model `OrderRequest` is used to define the structure for API requests
# when placing or describing an order. It mirrors what we expect an `omspy.order.Order` object
# might encapsulate.

# Conceptual `omspy.order.Order` usage:
# ```python
# from omspy.order import Order
#
# # Basic limit order
# order = Order(
#     symbol="INFY-EQ",
#     quantity=1,
#     side="BUY", # omspy might use 'side', Zerodha expects 'transaction_type'
#     order_type="LIMIT",
#     product="CNC",
#     exchange="NSE",
#     price=1300.00
# )
#
# # Order with extra attributes
# stoploss_order = Order(
#     symbol="SBIN-EQ",
#     quantity=10,
#     side="SELL",
#     order_type="SL", # Stop-loss Limit
#     product="MIS",
#     exchange="NSE",
#     price=570.00,      # Limit price for the SL order
#     trigger_price=575.00, # Price at which the limit order is triggered
#     validity="DAY",
#     tag="my_sbi_stoploss"
# )
#
# # omspy's Order object would then likely have a method to convert to a dictionary
# # suitable for the broker, or the broker's place_order method would accept the Order object.
# # order_payload = order.to_broker_format() # Fictional method
# ```

# The mock `Order` class defined at the top of this file (within the ImportError block)
# already demonstrates how these attributes might be structured and includes a `to_dict()`
# method that performs mappings like 'side' -> 'transaction_type'.
#
# Key attributes and their typical Zerodha mappings:
# - `symbol`: (omspy) -> `tradingsymbol` (Zerodha). Example: "INFY-EQ", "NIFTY23AUGFUT".
# - `quantity`: Number of shares/lots.
# - `side`: (omspy: "BUY" or "SELL") -> `transaction_type` (Zerodha: "BUY" or "SELL").
# - `order_type`: (omspy/Zerodha) "MARKET", "LIMIT", "SL" (Stoploss Limit), "SL-M" (Stoploss Market).
# - `product`: (omspy/Zerodha) "CNC" (Cash and Carry), "MIS" (Margin Intraday Squareoff), "NRML" (Normal).
# - `exchange`: (omspy/Zerodha) "NSE", "BSE", "NFO", "CDS", "MCX".
# - `price`: Required for "LIMIT" and "SL" orders.
# - `trigger_price`: Required for "SL" and "SL-M" orders. The price at which a limit or market order is triggered.
# - `validity`: Typically "DAY" (valid for the trading day) or "IOC" (Immediate or Cancel).
# - `disclosed_quantity`: For iceberg orders.
# - `tag`: An optional tag for identifying orders, often for strategy tracking (Zerodha supports this).

@app.get("/orders/example_payload", response_model=OrderRequest, tags=["2. Order Object & Attributes"])
async def get_order_example_payload():
    """
    ## 2. Understanding the Order Object and Attributes

    This endpoint returns an example payload for placing an order.
    It's based on the `OrderRequest` Pydantic model, which defines the expected structure.

    When using `omspy`, you would typically create an `Order` object from `omspy.order`
    and populate its attributes. This object (or a dictionary derived from it)
    would then be passed to the broker's order placement method.

    **Key Standard Attributes:**
    *   `symbol`: e.g., "INFY-EQ", "RELIANCE-EQ", "NIFTY23JUL FUT"
    *   `quantity`: Number of shares or lots.
    *   `side`: "BUY" or "SELL". `omspy` might use `side`, which would be mapped to `transaction_type` for Zerodha.
    *   `order_type`: "MARKET", "LIMIT", "SL" (stop-loss limit), "SL-M" (stop-loss market).
    *   `product`: "CNC" (long-term equity), "MIS" (intraday equity/F&O), "NRML" (overnight F&O).
    *   `exchange`: "NSE", "BSE", "NFO", "MCX", etc.
    *   `price`: Required for LIMIT and SL orders. The price at which you want to buy/sell.

    **Common Extra Attributes (often supported by brokers like Zerodha):**
    *   `trigger_price`: For SL and SL-M orders. The price at which your main order gets activated.
    *   `validity`: "DAY" (valid for the day), "IOC" (Immediate Or Cancel).
    *   `disclosed_quantity`: For iceberg orders (showing only a part of the total quantity).
    *   `tag`: A custom tag for your reference (supported by Zerodha).

    The `OrderRequest` model in this tutorial includes these fields.
    The mock `Order` class (used if `omspy` is not installed) also reflects these attributes
    and includes a `to_dict()` method that handles mapping `side` to `transaction_type`
    for compatibility with Zerodha's expected field names.
    """
    return OrderRequest.Config.schema_extra["example"]


# --- 3. Placing Orders ---

def _ensure_broker_connected():
    """Helper function to check for broker connection."""
    if not broker:
        raise HTTPException(
            status_code=403,
            detail="Broker not connected. Please use the /connect endpoint first."
        )

async def _place_order_common(order_data: OrderRequest, expected_order_type: Optional[str] = None) -> OrderResponse:
    """Common logic for placing an order."""
    _ensure_broker_connected()
    if expected_order_type and order_data.order_type.upper() != expected_order_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid order_type for this endpoint. Expected {expected_order_type}, got {order_data.order_type}."
        )

    # Create an Order instance (using our mock or a real omspy.order.Order)
    # The mock Order class's to_dict() method handles mapping 'side' to 'transaction_type'
    # and other potential transformations needed for the broker.
    oms_order = Order(
        symbol=order_data.symbol,
        quantity=order_data.quantity,
        side=order_data.side.upper(), # Ensure BUY/SELL are uppercase
        order_type=order_data.order_type.upper(),
        product=order_data.product.upper(),
        exchange=order_data.exchange.upper(),
        price=order_data.price,
        trigger_price=order_data.trigger_price,
        validity=(order_data.validity.upper() if order_data.validity is not None else "DAY"),
        disclosed_quantity=order_data.disclosed_quantity,
        tag=order_data.tag
        # any other params from order_data.extra_params if we had it
    )

    try:
        # The broker.order_place method is assumed to take a dictionary.
        # Our mock Order class has a to_dict() method.
        # A real omspy Order class would likely have a similar method or be directly passable.
        order_payload = oms_order.to_dict() # Convert Order object to dict for the broker

        # Validate required fields for specific order types
        if oms_order.order_type == "LIMIT" and oms_order.price is None:
            raise HTTPException(status_code=400, detail="Price is required for LIMIT orders.")
        if oms_order.order_type == "SL" and (oms_order.price is None or oms_order.trigger_price is None):
            raise HTTPException(status_code=400, detail="Price and Trigger Price are required for SL orders.")
        if oms_order.order_type == "SL-M" and oms_order.trigger_price is None:
            raise HTTPException(status_code=400, detail="Trigger Price is required for SL-M orders.")

        # For MARKET orders, Zerodha (and many brokers) might not accept a price.
        # If a price is provided for a MARKET order, it's often ignored or could cause an error.
        # We'll ensure price is None for MARKET orders before sending to broker.
        if oms_order.order_type == "MARKET":
            order_payload["price"] = None # Explicitly set price to None for market orders

        # broker is global and initialized via /connect
        result = broker.order_place(order=order_payload) # type: ignore

        return OrderResponse(
            order_id=str(result.get("order_id")),
            status=str(result.get("status", "UNKNOWN")),
            message=f"{oms_order.order_type} order placement initiated.",
            details=result
        )
    except HTTPException: # Re-raise HTTPExceptions from validations
        raise
    except AttributeError: # If broker is None (though _ensure_broker_connected should catch this)
         raise HTTPException(status_code=500, detail="Broker instance not available.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error placing order: {str(e)}")


@app.post("/orders/place/market", response_model=OrderResponse, tags=["3. Placing Orders"])
async def place_market_order(order_data: OrderRequest):
    """
    ### Place a Market Order

    A market order is an order to buy or sell a security immediately at the best available current price.
    It guarantees execution but not the price.

    **Required fields from `OrderRequest` for Market Order:**
    - `symbol`
    - `quantity`
    - `side` (BUY/SELL)
    - `order_type`: Must be "MARKET"
    - `product` (CNC, MIS, NRML)
    - `exchange` (NSE, BSE, etc.)

    *Price should ideally not be sent or will be ignored by the broker for market orders.*
    """
    if order_data.order_type.upper() != "MARKET":
        raise HTTPException(status_code=400, detail="Order type must be MARKET for this endpoint.")
    # For market orders, ensure price is not considered critical or is None
    order_data.price = None
    return await _place_order_common(order_data, expected_order_type="MARKET")


@app.post("/orders/place/limit", response_model=OrderResponse, tags=["3. Placing Orders"])
async def place_limit_order(order_data: OrderRequest):
    """
    ### Place a Limit Order

    A limit order is an order to buy or sell a security at a specific price or better.
    A buy limit order can only be executed at the limit price or lower, and a sell limit order can only be executed at the limit price or higher.
    Execution is not guaranteed if the market doesn't reach your limit price.

    **Required fields from `OrderRequest` for Limit Order:**
    - `symbol`
    - `quantity`
    - `side` (BUY/SELL)
    - `order_type`: Must be "LIMIT"
    - `product`
    - `exchange`
    - `price`: The specific price at which to execute the order.
    """
    if order_data.order_type.upper() != "LIMIT":
        raise HTTPException(status_code=400, detail="Order type must be LIMIT for this endpoint.")
    if order_data.price is None:
        raise HTTPException(status_code=400, detail="`price` is required for LIMIT orders.")
    return await _place_order_common(order_data, expected_order_type="LIMIT")


@app.post("/orders/place/sl", response_model=OrderResponse, tags=["3. Placing Orders"])
async def place_stoploss_limit_order(order_data: OrderRequest):
    """
    ### Place a Stop-Loss Limit (SL) Order

    A stop-loss limit order consists of two prices: a trigger price and a limit price.
    When the security's price reaches or passes the trigger price, a limit order is placed at the specified limit price.
    This helps protect against significant losses or lock in profits.

    - For a **BUY SL order**: Trigger Price > Current Market Price. Limit Price >= Trigger Price.
      Order is placed when Last Traded Price (LTP) >= Trigger Price.
    - For a **SELL SL order**: Trigger Price < Current Market Price. Limit Price <= Trigger Price.
      Order is placed when Last Traded Price (LTP) <= Trigger Price.


    **Required fields from `OrderRequest` for SL Order:**
    - `symbol`
    - `quantity`
    - `side` (BUY/SELL)
    - `order_type`: Must be "SL"
    - `product`
    - `exchange`
    - `price`: The limit price for the order once triggered.
    - `trigger_price`: The price at which the limit order is activated.
    """
    if order_data.order_type.upper() != "SL":
        raise HTTPException(status_code=400, detail="Order type must be SL for this endpoint.")
    if order_data.price is None or order_data.trigger_price is None:
        raise HTTPException(status_code=400, detail="`price` and `trigger_price` are required for SL orders.")
    # Basic validation for SL order prices (can be more complex depending on broker rules)
    if order_data.side.upper() == "BUY" and order_data.price < order_data.trigger_price:
        # This is a common convention, but broker rules vary. Zerodha is flexible here.
        # For simplicity, we'll allow it but one might add stricter validation.
        pass # raise HTTPException(status_code=400, detail="For BUY SL, price should generally be >= trigger_price.")
    if order_data.side.upper() == "SELL" and order_data.price > order_data.trigger_price:
        pass # raise HTTPException(status_code=400, detail="For SELL SL, price should generally be <= trigger_price.")
    return await _place_order_common(order_data, expected_order_type="SL")


@app.post("/orders/place/slm", response_model=OrderResponse, tags=["3. Placing Orders"])
async def place_stoploss_market_order(order_data: OrderRequest):
    """
    ### Place a Stop-Loss Market (SL-M) Order

    A stop-loss market order has only a trigger price.
    When the security's price reaches or passes the trigger price, a market order is placed.
    This guarantees execution once triggered but not the price (similar to a regular market order).

    - For a **BUY SL-M order**: Trigger Price > Current Market Price.
      Market order is placed when Last Traded Price (LTP) >= Trigger Price.
    - For a **SELL SL-M order**: Trigger Price < Current Market Price.
      Market order is placed when Last Traded Price (LTP) <= Trigger Price.

    **Required fields from `OrderRequest` for SL-M Order:**
    - `symbol`
    - `quantity`
    - `side` (BUY/SELL)
    - `order_type`: Must be "SL-M"
    - `product`
    - `exchange`
    - `trigger_price`: The price at which the market order is activated.

    *`price` should not be provided for SL-M orders as it becomes a market order.*
    """
    if order_data.order_type.upper() != "SL-M":
        raise HTTPException(status_code=400, detail="Order type must be SL-M for this endpoint.")
    if order_data.trigger_price is None:
        raise HTTPException(status_code=400, detail="`trigger_price` is required for SL-M orders.")
    order_data.price = None # Ensure price is None for SL-M as it's a market order post-trigger
    return await _place_order_common(order_data, expected_order_type="SL-M")


# --- 4. Modifying Orders ---

@app.put("/orders/modify/{order_id}", response_model=OrderResponse, tags=["4. Modifying Orders"])
async def modify_pending_order(order_id: str, changes: ModifyOrderRequest):
    """
    ### Modify a Pending Order

    This endpoint allows modification of certain parameters of a pending (open) order.
    Not all parameters can be modified, and this varies by broker.
    Typically, you can modify:
    - `quantity` (usually only if increasing for an open order, or if partially filled)
    - `price` (for limit orders)
    - `trigger_price` (for stop-loss orders)
    - `order_type` (less common, e.g., changing LIMIT to SL, but often restricted)

    **Important Considerations:**
    - You can only modify orders that are still open and pending execution.
    - Modifying an order might change its priority in the order book.
    - The `order_id` is the ID received when the order was first placed.

    **`omspy` Conceptual Usage:**
    ```python
    # Assuming 'broker' is your connected omspy Zerodha instance
    # modified_details = broker.order_modify(
    #     order_id="YOUR_ORDER_ID",
    #     quantity=new_quantity, # Optional
    #     price=new_price,       # Optional
    #     trigger_price=new_trigger_price, # Optional
    #     order_type=new_order_type # Optional, if supported
    # )
    ```

    This endpoint will:
    1. Ensure the broker is connected.
    2. Construct a dictionary of parameters to change from the `ModifyOrderRequest`.
    3. Call the `broker.order_modify()` method.
    """
    _ensure_broker_connected()

    if not order_id:
        raise HTTPException(status_code=400, detail="Order ID is required.")

    update_params = changes.dict(exclude_unset=True) # Get only provided fields

    if not update_params:
        raise HTTPException(status_code=400, detail="No parameters provided for modification.")

    # Ensure values are uppercase if they are enum-like string fields
    if "order_type" in update_params and update_params["order_type"]:
        update_params["order_type"] = update_params["order_type"].upper()
    # Potentially other fields like 'product' or 'validity' if they were modifiable
    # and part of ModifyOrderRequest.

    try:
        # broker is global and initialized via /connect
        # The mock broker.order_modify takes order_id and then kwargs for changes.
        result = broker.order_modify(order_id=order_id, **update_params) # type: ignore

        return OrderResponse(
            order_id=str(result.get("order_id", order_id)), # Use original order_id if not in result
            status=str(result.get("status", "MODIFIED_UNKNOWN_STATUS")), # Or a more specific status
            message=f"Order {order_id} modification request processed.",
            details=result
        )
    except AttributeError: # If broker is None
         raise HTTPException(status_code=500, detail="Broker instance not available.")
    except Exception as e:
        # This could be an error from the broker API (e.g., order already executed, invalid params)
        raise HTTPException(status_code=500, detail=f"Error modifying order {order_id}: {str(e)}")


# --- 5. Cancelling Orders ---

@app.delete("/orders/cancel/{order_id}", response_model=OrderResponse, tags=["5. Cancelling Orders"])
async def cancel_pending_order(order_id: str):
    """
    ### Cancel a Pending Order

    This endpoint allows for the cancellation of a pending (open) order.
    You can only cancel orders that have not yet been executed or partially executed and closed.

    **Important Considerations:**
    - If an order is already fully executed, it cannot be cancelled.
    - If an order is partially executed, you can typically cancel the remaining open quantity.
    - The `order_id` is the ID received when the order was first placed.

    **`omspy` Conceptual Usage:**
    ```python
    # Assuming 'broker' is your connected omspy Zerodha instance
    # cancellation_details = broker.order_cancel(order_id="YOUR_ORDER_ID")
    ```

    This endpoint will:
    1. Ensure the broker is connected.
    2. Call the `broker.order_cancel()` method with the provided `order_id`.
    """
    _ensure_broker_connected()

    if not order_id:
        raise HTTPException(status_code=400, detail="Order ID is required for cancellation.")

    try:
        # broker is global and initialized via /connect
        # The mock broker.order_cancel takes order_id.
        result = broker.order_cancel(order_id=order_id) # type: ignore

        return OrderResponse(
            order_id=str(result.get("order_id", order_id)), # Use original order_id if not in result
            status=str(result.get("status", "CANCELLED_UNKNOWN_STATUS")), # Or a more specific status like "CANCELLED"
            message=f"Order {order_id} cancellation request processed.",
            details=result
        )
    except AttributeError: # If broker is None
         raise HTTPException(status_code=500, detail="Broker instance not available.")
    except Exception as e:
        # This could be an error from the broker API (e.g., order already executed/cancelled, invalid order_id)
        raise HTTPException(status_code=500, detail=f"Error cancelling order {order_id}: {str(e)}")


# --- 6. Getting Order Information ---

class HistoricalOrder(OrderRequest): # Reuse OrderRequest for structure, add status and id
    order_id: str
    status: str
    average_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    pending_quantity: Optional[int] = None
    order_timestamp: Optional[str] = None # Example: "2023-07-26 10:00:00"
    # Potentially more fields like transaction_type_actual if different from 'side'
    # message: Optional[str] = None # Any message from broker


@app.get("/orders/history", response_model=List[HistoricalOrder], tags=["6. Getting Order Information"])
async def get_order_history_list():
    """
    ### Get Order History

    Fetches a list of orders placed. This might be all orders for the day,
    or a more extensive history depending on the broker's API and `omspy`'s implementation.

    **`omspy` Conceptual Usage:**
    ```python
    # orders = broker.orders  # If it's a property
    # # OR
    # orders = broker.get_orders() # If it's a method
    ```

    The response will be a list of order details.
    """
    _ensure_broker_connected()
    try:
        # Assuming broker.orders is a property returning a list of order dicts
        # or broker.get_orders() returns the same.
        # Our mock has 'broker.orders' as a property.
        orders_data = broker.orders # type: ignore

        # We need to map the data from the broker to our HistoricalOrder model.
        # This is a simplified mapping. A real scenario might involve more complex transformations.
        history = []
        for order_detail in orders_data:
            # Basic mapping, assuming broker response matches HistoricalOrder fields closely
            # or we adapt them here.
            hist_order = HistoricalOrder(
                order_id=str(order_detail.get("order_id", "N/A")),
                symbol=str(order_detail.get("symbol", order_detail.get("tradingsymbol", "N/A"))),
                quantity=int(order_detail.get("quantity", 0)),
                side=str(order_detail.get("side", order_detail.get("transaction_type", "N/A"))).upper(),
                order_type=str(order_detail.get("order_type", "N/A")).upper(),
                product=str(order_detail.get("product", "N/A")).upper(),
                exchange=str(order_detail.get("exchange", "N/A")).upper(),
                price=float(order_detail["price"]) if order_detail.get("price") is not None else None,
                trigger_price=float(order_detail["trigger_price"]) if order_detail.get("trigger_price") is not None else None,
                status=str(order_detail.get("status", "UNKNOWN")),
                average_price=float(order_detail["average_price"]) if order_detail.get("average_price") is not None else None,
                filled_quantity=int(order_detail["filled_quantity"]) if order_detail.get("filled_quantity") is not None else None,
                # pending_quantity can often be calculated: quantity - filled_quantity
                order_timestamp=str(order_detail.get("order_timestamp", ""))
                # tag, validity, disclosed_quantity could also be added if present
            )
            history.append(hist_order)
        return history
    except AttributeError:
         raise HTTPException(status_code=500, detail="Broker instance not available or 'orders' property missing.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order history: {str(e)}")


@app.get("/orders/status/{order_id}", response_model=HistoricalOrder, tags=["6. Getting Order Information"])
async def get_specific_order_status(order_id: str):
    """
    ### Get Status of a Specific Order

    Fetches the current status and details of a single order by its `order_id`.
    This is useful for tracking an order's lifecycle (e.g., PENDING, OPEN, COMPLETE, REJECTED, CANCELLED).

    **`omspy` Conceptual Usage:**
    ```python
    # order_details = broker.get_order_history(order_id="YOUR_ORDER_ID") # Zerodha specific
    # # OR
    # order_details = broker.get_order_status(order_id="YOUR_ORDER_ID") # More generic
    ```
    The response will contain details for the specified order.
    """
    _ensure_broker_connected()
    if not order_id:
        raise HTTPException(status_code=400, detail="Order ID is required.")
    try:
        # Assuming a method like get_order_history(order_id) or get_order_status(order_id)
        # Our mock has broker.get_order_history(order_id) which returns a list,
        # but for a single order status, we might expect a single dict or the first item.
        # Let's assume it returns a list of states for that order, and we take the latest/most relevant.
        # For simplicity with the current mock, we'll assume it returns a list and we take the first.
        # A real API might return a single object directly.

        order_details_list = broker.get_order_history(order_id=order_id) # type: ignore

        if not order_details_list:
            raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found or no history.")

        # Assuming the first entry is the most relevant or a summary
        order_detail = order_details_list[0] if isinstance(order_details_list, list) else order_details_list

        # Map to HistoricalOrder
        hist_order = HistoricalOrder(
            order_id=str(order_detail.get("order_id", order_id)),
            symbol=str(order_detail.get("symbol", order_detail.get("tradingsymbol", "N/A"))),
            quantity=int(order_detail.get("quantity", 0)),
            side=str(order_detail.get("side", order_detail.get("transaction_type", "N/A"))).upper(),
            order_type=str(order_detail.get("order_type", "N/A")).upper(),
            product=str(order_detail.get("product", "N/A")).upper(),
            exchange=str(order_detail.get("exchange", "N/A")).upper(),
            price=float(order_detail["price"]) if order_detail.get("price") is not None else None,
            trigger_price=float(order_detail["trigger_price"]) if order_detail.get("trigger_price") is not None else None,
            status=str(order_detail.get("status", "UNKNOWN")),
            average_price=float(order_detail["average_price"]) if order_detail.get("average_price") is not None else None,
            filled_quantity=int(order_detail["filled_quantity"]) if order_detail.get("filled_quantity") is not None else None,
            order_timestamp=str(order_detail.get("order_timestamp", ""))
        )
        return hist_order
    except AttributeError:
         raise HTTPException(status_code=500, detail="Broker instance not available or method missing.")
    except HTTPException: # Re-raise 404 if order not found
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching status for order {order_id}: {str(e)}")


# --- 7. Other Useful Features (Examples) ---

# Pydantic Models for this section
class EquityMargin(BaseModel):
    available_margin: Optional[float] = Field(None, example=100000.50)
    used_margin: Optional[float] = Field(None, example=5000.20)
    payin: Optional[float] = Field(None, example=0.0)
    # Add other relevant fields like 'collateral', 'live_balance' etc. if typically provided

class CommodityMargin(BaseModel): # Example if broker provides separate commodity margins
    available_margin: Optional[float] = Field(None, example=50000)
    used_margin: Optional[float] = Field(None, example=1000)

class FundsResponse(BaseModel):
    equity: Optional[EquityMargin] = None
    commodity: Optional[CommodityMargin] = None
    # Potentially other segments like 'currency'
    message: Optional[str] = None

class Position(BaseModel):
    symbol: str = Field(..., example="RELIANCE-EQ")
    exchange: Optional[str] = Field(None, example="NSE")
    product: Optional[str] = Field(None, example="CNC")
    quantity: int = Field(..., example=10)
    average_price: Optional[float] = Field(None, example=2500.00)
    ltp: Optional[float] = Field(None, example=2550.50)
    pnl: Optional[float] = Field(None, example=505.00)
    # Add other fields like 'day_pnl', 'm2m', 'unrealized_pnl', 'realized_pnl' etc.
    # 'buy_value', 'sell_value', 'net_value'

class PositionsResponse(BaseModel):
    net: List[Position] = [] # Net positions
    day: Optional[List[Position]] = None # Day-wise positions if provided separately
    message: Optional[str] = None

class OHLC(BaseModel):
    open: float
    high: float
    low: float
    close: float

class QuoteResponse(BaseModel):
    symbol: str
    exchange: Optional[str] = None
    ltp: float
    last_quantity: Optional[int] = None
    average_price: Optional[float] = None # Average traded price for the day
    volume: Optional[int] = None
    total_buy_quantity: Optional[int] = None
    total_sell_quantity: Optional[int] = None
    ohlc: OHLC
    change: Optional[float] = None # Absolute change
    change_percent: Optional[float] = None # Percentage change
    # last_trade_time: Optional[datetime] # Using str for simplicity if needed
    # depth: Optional[Dict] # For market depth
    message: Optional[str] = None

# --- 8. Error Handling and Best Practices (Conceptual - covered in endpoint docstrings & code) ---

# This section is primarily covered by:
# 1.  The use of `try-except` blocks within each endpoint to catch potential errors
#     from the (mock) broker interaction or other issues, returning `HTTPException`
#     with appropriate status codes and messages.
# 2.  The `_ensure_broker_connected()` helper, which centralizes the check for an active
#     broker connection.
# 3.  Pydantic models for request validation, which FastAPI uses automatically.
# 4.  Docstrings within each endpoint often mention specific error conditions or
#     important considerations.

# Key Error Handling Concepts for a Real Implementation:
# -   **Broker-Specific Errors:** `omspy` would likely translate errors from the underlying
#     broker API (e.g., Kite Connect errors) into Python exceptions or specific
#     return codes/messages. These could include:
#     -   Authentication failures (invalid credentials, expired session, 2FA issues).
#     -   Order validation errors (incorrect parameters, insufficient funds, margin issues,
#         invalid symbol, quantity, price, market closed, etc.).
#     -   Network issues or API downtime.
#     -   Rate limit exceeded.
# -   **`omspy` Exceptions:** A well-designed library like `omspy` might have its own
#     hierarchy of exceptions (e.g., `omspy.exceptions.APIError`,
#     `omspy.exceptions.AuthenticationError`, `omspy.exceptions.OrderException`).
#     Your code should be prepared to catch these specific exceptions.
# -   **Logging:** Comprehensive logging is crucial in production to trace issues. Log
#     requests, responses (especially error responses), and any exceptions encountered.

# Best Practices Discussed/Implemented in this Tutorial:
# -   **Credential Security:** Explicitly warned against hardcoding credentials. Suggested
#     using environment variables, config files, or secrets managers (see `/connect` endpoint).
# -   **Input Validation:**
#     -   FastAPI uses Pydantic for basic request validation (data types, required fields).
#     -   Custom validation is added within endpoints for specific conditions (e.g., price
#         for LIMIT orders, `order_type` matching the endpoint).
# -   **Modular Design:**
#     -   Helper function `_ensure_broker_connected()` for reuse.
#     -   Helper function `_place_order_common()` for common order placement logic.
# -   **Clear API Design:**
#     -   Using FastAPI's features like Pydantic models for request/response, path/query
#         parameters, and automatic documentation.
#     -   Informative docstrings for each endpoint.
# -   **Mocking for Development/Testing:** The use of mock `Zerodha` and `Order` classes
#     demonstrates how to develop and test the API layer independently of the live
#     broker connection, which is a very good practice.
# -   **Configuration Management (Conceptual):** While credentials are global for simplicity
#     here, in a real app, a more robust configuration system would be used.

# Further Best Practices for Production Systems:
# -   **Idempotency:** For critical operations like order placement, consider how to handle
#     retries safely to avoid duplicate orders (e.g., using a unique client order ID).
# -   **Rate Limiting:** Be mindful of the broker's API rate limits and implement client-side
#     throttling or queuing if necessary.
# -   **Comprehensive Testing:** Test thoroughly, including edge cases and error conditions,
#     ideally with a paper trading account before live trading.
# -   **Asynchronous Operations:** For potentially long-running broker operations, consider
#     background tasks (e.g., using `fastapi.BackgroundTasks` or a task queue like Celery)
#     to avoid blocking the server, though `async/await` already helps with I/O-bound tasks.
# -   **Graceful Shutdown:** Ensure your application handles signals (like SIGTERM) gracefully,
#     cancelling any pending operations or saving state if needed.


@app.get("/account/funds", response_model=FundsResponse, tags=["7. Other Useful Features"])
async def get_account_funds():
    """
    ### Get Account Funds & Margins

    Fetches available funds, margins, and other account balance related details.
    The structure of the response can vary significantly between brokers.

    **`omspy` Conceptual Usage:**
    ```python
    # funds_details = broker.funds  # If it's a property
    # # OR
    # funds_details = broker.get_funds() # If it's a method
    ```
    """
    _ensure_broker_connected()
    try:
        # Our mock broker has 'broker.funds' as a property
        funds_data = broker.funds # type: ignore

        # Direct mapping if funds_data structure matches FundsResponse
        # This is highly dependent on the actual structure returned by omspy/broker
        equity_margin_data = funds_data.get("equity", {})
        commodity_margin_data = funds_data.get("commodity", {})

        return FundsResponse(
            equity=EquityMargin(**equity_margin_data) if equity_margin_data else None,
            commodity=CommodityMargin(**commodity_margin_data) if commodity_margin_data else None,
            message="Funds details retrieved successfully."
        )
    except AttributeError:
         raise HTTPException(status_code=500, detail="Broker instance not available or 'funds' property missing.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching account funds: {str(e)}")

@app.get("/account/positions", response_model=PositionsResponse, tags=["7. Other Useful Features"])
async def get_account_positions():
    """
    ### Get Account Positions

    Fetches the current open positions in the account.
    This typically includes details like symbol, quantity, average price, P&L, etc.
    Brokers might provide 'net' positions (overall) and 'day' positions (for the current trading day).

    **`omspy` Conceptual Usage:**
    ```python
    # positions_details = broker.positions # If it's a property
    # # OR
    # positions_details = broker.get_positions() # If it's a method
    ```
    """
    _ensure_broker_connected()
    try:
        # Our mock broker has 'broker.positions' as a property returning a list for 'net'
        positions_raw_data = broker.positions # type: ignore

        net_positions = []
        if isinstance(positions_raw_data, list): # Assuming it's a list of net positions
            for pos_data in positions_raw_data:
                net_positions.append(Position(**pos_data))
        elif isinstance(positions_raw_data, dict): # If it's a dict with 'net' and 'day' keys
             for pos_data in positions_raw_data.get("net", []):
                 net_positions.append(Position(**pos_data))
             # Could also process day positions if needed:
             # day_positions_data = positions_raw_data.get("day", [])

        return PositionsResponse(
            net=net_positions,
            message="Positions retrieved successfully."
        )
    except AttributeError:
         raise HTTPException(status_code=500, detail="Broker instance not available or 'positions' property missing.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching account positions: {str(e)}")


@app.get("/market/quote/{exchange}/{symbol}", response_model=QuoteResponse, tags=["7. Other Useful Features"])
async def get_market_quote(exchange: str, symbol: str):
    """
    ### Get Market Quote

    Fetches a live market quote for a given symbol on a specific exchange.
    A quote typically includes Last Traded Price (LTP), Open, High, Low, Close (OHLC), volume, etc.

    **Path Parameters:**
    - `exchange`: The exchange of the symbol (e.g., NSE, BSE, NFO, MCX).
    - `symbol`: The trading symbol (e.g., INFY-EQ, RELIANCE, BANKNIFTY23AUGFUT).

    **`omspy` Conceptual Usage:**
    ```python
    # quote_details = broker.quote(symbol="INFY-EQ", exchange="NSE")
    # # OR, if exchange is part of symbol for omspy
    # quote_details = broker.get_quote(instrument="NSE:INFY-EQ")
    ```
    """
    _ensure_broker_connected()
    if not symbol or not exchange:
        raise HTTPException(status_code=400, detail="Symbol and Exchange are required.")
    try:
        # Our mock broker has broker.quote(symbol, exchange)
        # The actual omspy might take a single instrument string like "NSE:INFY"
        quote_data = broker.quote(symbol=symbol.upper(), exchange=exchange.upper()) # type: ignore

        # Map to QuoteResponse, assuming quote_data structure matches
        # This is highly dependent on the actual structure
        ohlc_data = quote_data.get("ohlc", {})

        return QuoteResponse(
            symbol=str(quote_data.get("symbol", symbol)),
            exchange=str(quote_data.get("exchange", exchange)),
            ltp=float(quote_data.get("ltp", 0.0)),
            last_quantity=int(quote_data["last_quantity"]) if quote_data.get("last_quantity") is not None else None,
            average_price=float(quote_data["average_price"]) if quote_data.get("average_price") is not None else None,
            volume=int(quote_data["volume"]) if quote_data.get("volume") is not None else None,
            total_buy_quantity=int(quote_data["total_buy_quantity"]) if quote_data.get("total_buy_quantity") is not None else None,
            total_sell_quantity=int(quote_data["total_sell_quantity"]) if quote_data.get("total_sell_quantity") is not None else None,
            ohlc=OHLC(**ohlc_data) if ohlc_data else OHLC(open=0,high=0,low=0,close=0), # Ensure OHLC is always present
            change=float(quote_data["change"]) if quote_data.get("change") is not None else None,
            change_percent=float(quote_data["change_percent"]) if quote_data.get("change_percent") is not None else None,
            message="Quote retrieved successfully."
        )
    except AttributeError:
         raise HTTPException(status_code=500, detail="Broker instance not available or 'quote' method missing.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quote for {symbol}: {str(e)}")


# --- Configuration and Authentication ---

@app.post("/connect", response_model=ConnectionResponse, tags=["1. Configuration & Authentication"])
async def connect_to_broker(creds: ConnectionRequest):
    """
    ## 1. Connect to Zerodha via omspy

    This endpoint simulates connecting to the Zerodha broker.
    In a real scenario, `omspy` would use these credentials to authenticate with Zerodha (likely via Kite Connect API).

    **IMPORTANT:**
    - **Never hardcode your actual credentials in production code.**
    - Use environment variables, a configuration file, or a secrets management service.
    - This tutorial stores them in a global variable for simplicity only.

    **`omspy` `Zerodha` Broker Initialization (Conceptual):**
    ```python
    # from omspy.brokers.zerodha import Zerodha
    # broker = Zerodha(
    #     userid="YOUR_USER_ID",
    #     password="YOUR_PASSWORD",
    #     apikey="YOUR_API_KEY",
    #     secret="YOUR_API_SECRET",
    #     pin="YOUR_PIN" # For 2FA
    # )
    # broker.authenticate() # Or this might be handled during instantiation
    ```

    This endpoint will:
    1. Store the provided credentials (for tutorial demonstration).
    2. Instantiate the `Zerodha` broker object from `omspy.brokers.zerodha`.
       (Here, we'll use our mock `Zerodha` class if `omspy` is not available).
    3. Attempt to authenticate (mocked in our fallback).
    """
    global broker, CREDENTIALS

    CREDENTIALS["user_id"] = creds.user_id
    CREDENTIALS["password"] = creds.password
    CREDENTIALS["api_key"] = creds.api_key
    CREDENTIALS["api_secret"] = creds.api_secret
    CREDENTIALS["pin"] = creds.pin

    try:
        # In a real app, you'd pass the actual credentials.
        # For this tutorial, we're using the globally stored ones for simplicity
        # if the broker object needs them directly on init, or omspy handles them internally.
        # The mock Zerodha class takes them for demonstration.
        broker = Zerodha(
            userid=CREDENTIALS["user_id"],
            password=CREDENTIALS["password"],
            apikey=CREDENTIALS["api_key"],
            secret=CREDENTIALS["api_secret"],
            pin=CREDENTIALS["pin"]
        )
        # Some libraries might have an explicit authenticate method,
        # others might do it during instantiation or first API call.
        # Our mock has an authenticate method.
        if hasattr(broker, 'authenticate') and callable(getattr(broker, 'authenticate')):
            if not broker.authenticate(): # type: ignore
                raise HTTPException(status_code=401, detail="Broker authentication failed (mocked).")

        return ConnectionResponse(
            message="Successfully connected to broker (mocked). Ready to place orders.",
            user_id=CREDENTIALS["user_id"]
        )
    except ImportError:
        # This case should ideally be handled by the initial try-except for omspy imports,
        # but as a fallback for the endpoint itself:
        raise HTTPException(status_code=500, detail="omspy library not found. Cannot connect.")
    except Exception as e:
        # Reset broker instance if connection fails
        broker = None
        raise HTTPException(status_code=500, detail=f"Failed to connect to broker: {str(e)}")


@app.get("/connection_status", response_model=ConnectionResponse, tags=["1. Configuration & Authentication"])
async def get_connection_status():
    """
    Check the current connection status to the broker.
    """
    global broker
    if broker and CREDENTIALS.get("user_id"):
        return ConnectionResponse(message="Broker is connected.", user_id=CREDENTIALS["user_id"])
    return ConnectionResponse(message="Broker is not connected.", user_id=None)


@app.get("/", tags=["General"])
async def root():
    """
    Root path for the tutorial API.
    Provides a welcome message and basic information.
    """
    return {
        "message": "Welcome to the omspy Zerodha Broker API Tutorial!",
        "documentation": "/docs",
        "omspy_info": "This tutorial assumes omspy is used for broker interaction.",
        "broker_status": "Not connected" if not broker else "Connected"
    }

if __name__ == "__main__":
    import uvicorn
    # It's good practice to only run the server this way for development.
    # For production, use a proper ASGI server like Uvicorn or Hypercorn directly.
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
Placeholder for further sections:
- Configuration and Authentication
- Order Object and Attributes
- Placing Orders (Market, Limit, SL, SL-M)
- Modifying Orders
- Cancelling Orders
- Getting Order Information (History, Status)
- Other Useful Features (Funds, Positions, Quotes)
- Error Handling
"""
