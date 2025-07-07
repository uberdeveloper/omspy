# Getting Started with `omspy` for Zerodha

## Introduction

`omspy` is a Python library designed to simplify interactions with various stock brokers by providing a unified Order Management System (OMS) interface. This tutorial will guide you through the basics of using `omspy` to connect to your Zerodha account, manage orders, and retrieve account information. We will focus on the `omspy.brokers.zerodha` module for broker-specific interactions and the `omspy.order.Order` class for defining order details.

By the end of this tutorial, you will be able to:

*   Authenticate with your Zerodha account using `omspy`.
*   Create and place different types of orders (Market, Limit, Stop-Loss).
*   Modify and cancel pending orders.
*   Fetch your order history, positions, and funds.
*   Get market quotes for instruments.

This guide assumes you are familiar with basic Python programming and trading concepts.

## Prerequisites

Before you begin, please ensure you have the following:

1.  **Python 3.7+:** `omspy` requires a modern version of Python. You can check your Python version by running `python --version` or `python3 --version` in your terminal.
2.  **`pip`:** Python's package installer, which usually comes with Python.
3.  **Zerodha Demat Account:** You need an active Zerodha trading and Demat account.
4.  **Zerodha Kite API Credentials:** You must have generated API credentials through the [Kite Developer Console](https://developers.kite.trade/). These include:
    *   `api_key`
    *   `api_secret`
    *   Your Zerodha `user_id`
    *   Your Kite account `password`
    *   Your 2FA (Two-Factor Authentication) `pin` or TOTP (Time-based One-Time Password) setup. `omspy` will likely require the PIN for session authentication.
5.  **Development Environment:** A code editor (like VS Code, PyCharm, etc.) and a terminal or command prompt.

## Installation

You can install `omspy` using `pip`. It's recommended to do this within a Python virtual environment.

```bash
pip install omspy
```

Depending on how `omspy` handles broker-specific dependencies, you might need to install an extra for Zerodha if available (this is a common pattern for libraries supporting multiple integrations):

```bash
# Example if omspy uses extras:
# pip install omspy[zerodha]
```
Consult the official `omspy` documentation for the precise installation command if extras are used. For this tutorial, we'll assume `pip install omspy` is sufficient to get the Zerodha broker components.

## Authentication with Zerodha

To interact with your Zerodha account, you first need to instantiate the `Zerodha` broker object from `omspy.brokers.zerodha` and authenticate.

```python
from omspy.brokers.zerodha import Zerodha
import os # For securely accessing credentials

# It's highly recommended to store your credentials securely,
# for example, as environment variables, and not hardcode them.
# Example using environment variables:
try:
    USER_ID = os.environ.get("ZERODHA_USER_ID")
    PASSWORD = os.environ.get("ZERODHA_PASSWORD")
    API_KEY = os.environ.get("ZERODHA_API_KEY")
    API_SECRET = os.environ.get("ZERODHA_API_SECRET")
    PIN = os.environ.get("ZERODHA_PIN") # Your 2FA PIN

    if not all([USER_ID, PASSWORD, API_KEY, API_SECRET, PIN]):
        raise ValueError("One or more Zerodha credentials environment variables are not set.")

except ValueError as e:
    print(f"Error: {e}")
    print("Please set ZERODHA_USER_ID, ZERODHA_PASSWORD, ZERODHA_API_KEY, ZERODHA_API_SECRET, and ZERODHA_PIN environment variables.")
    # exit() # You might want to exit if credentials are not found in a real script

# Initialize the Zerodha broker
# Ensure you have set the environment variables before running this.
# broker = Zerodha( # This line would be active in a real script
#     userid=USER_ID,
#     password=PASSWORD,
#     apikey=API_KEY,
#     secret=API_SECRET,
#     pin=PIN
# )

# For the purpose of this tutorial text, we'll assume 'broker' is magically available if the above were run.
# In your actual script, you would uncomment and use the instantiation above.
# For following examples, we'll just refer to 'broker'.
print("Conceptual: Broker instance would be created here if credentials are valid.")


# Authenticate with the broker
# Some libraries might authenticate during instantiation, while others
# require an explicit call. Check omspy's documentation.
# We'll assume an explicit authenticate method here for clarity.
try:
    # if hasattr(broker, 'authenticate') and callable(getattr(broker, 'authenticate')): # In a real script
    #     broker.authenticate()
    #     print(f"Successfully authenticated with Zerodha for user {USER_ID}!")
    # else:
    #     print(f"Broker instance created for {USER_ID}. Authentication might be implicit.")
    print(f"Conceptual: Authentication would be attempted here using 'broker.authenticate()' or implicitly.")

except Exception as e:
    print(f"Authentication failed: {e}")
    # Handle authentication failure (e.g., log error, notify user, exit)

# Now, the 'broker' object should be ready to use for placing orders,
# fetching data, etc., provided authentication was successful.
```

**Important Note on Credentials:**

*   **Never hardcode your API keys, passwords, or PINs directly into your scripts, especially if you plan to share or version control your code.**
*   The example above demonstrates loading credentials from environment variables, which is a more secure practice. You would set these variables in your operating system or using a `.env` file with a library like `python-dotenv`.

## Understanding `omspy.order.Order`

Once authenticated, you'll use the `omspy.order.Order` class to define the specifics of any order you want to place. This class acts as a standardized way to describe an order before it's sent to the broker.

First, import the `Order` class:

```python
from omspy.order import Order # Assuming this is the correct import path
```

The `Order` object is typically initialized with several key attributes that define your trade. Here are some of the most common ones, along with notes on how they map to Zerodha's terminology:

*   **`symbol` (str):** The trading symbol of the instrument.
    *   For Zerodha, this is often referred to as `tradingsymbol`.
    *   Examples: `"INFY-EQ"` (for Infosys on NSE Equity), `"RELIANCE"` (might need `"-EQ"` depending on `omspy`'s expectation or if `exchange` is also specified), `"NIFTY23AUGFUT"` (for Nifty August Futures), `"BANKNIFTY23AUG38000CE"` (for a Bank Nifty option).
*   **`quantity` (int):** The number of shares (for equity) or lots (for F&O) you want to trade. Must be a positive integer.
*   **`side` (str):** The direction of your trade.
    *   Typically `"BUY"` or `"SELL"`.
    *   Zerodha uses `transaction_type` for this, so `omspy` likely maps `side` to `transaction_type`.
*   **`order_type` (str):** The type of order you want to place. Common values:
    *   `"MARKET"`: Executes at the current best available market price.
    *   `"LIMIT"`: Executes only at your specified price or better. Requires the `price` attribute.
    *   `"SL"` (Stop-Loss Limit): A limit order that is triggered when the market price reaches your `trigger_price`. Requires both `price` and `trigger_price`.
    *   `"SL-M"` (Stop-Loss Market): A market order that is triggered when the market price reaches your `trigger_price`. Requires `trigger_price`.
*   **`product` (str):** The product type, indicating how the trade will be settled or its margin requirements. Common Zerodha product types:
    *   `"CNC"` (Cash and Carry): For delivery-based equity trades. No leverage.
    *   `"MIS"` (Margin Intraday Squareoff): For intraday trades with leverage. Positions are usually auto-squared off by the broker if not closed by the trader by a specified time.
    *   `"NRML"` (Normal): For overnight F&O positions or delivery-based equity trades where you might not want MIS benefits/restrictions.
*   **`exchange` (str, Optional):** The exchange on which to place the order.
    *   Examples: `"NSE"` (National Stock Exchange), `"BSE"` (Bombay Stock Exchange), `"NFO"` (NSE Futures & Options), `"CDS"` (NSE Currency Derivatives), `"MCX"` (Multi Commodity Exchange).
    *   `omspy` might infer the exchange from the symbol or require it explicitly.
*   **`price` (float, Optional):** The limit price for `LIMIT` and `SL` orders.
*   **`trigger_price` (float, Optional):** The price at which an `SL` or `SL-M` order is triggered and sent to the exchange.

**Common "Extra" Attributes:**

Many brokers, including Zerodha, support additional order parameters. `omspy`'s `Order` class might allow these as direct attributes or through a `kwargs` mechanism.

*   **`validity` (str, Optional):** How long the order remains active if not executed.
    *   `"DAY"` (Default for most orders): Valid for the current trading session.
    *   `"IOC"` (Immediate Or Cancel): Executed immediately for any portion available, and the rest is cancelled.
    *   (Zerodha also supports GTT - Good Till Triggered - orders, which are a separate mechanism usually not placed via the regular order placement method directly as a simple validity type).
*   **`disclosed_quantity` (int, Optional):** For iceberg orders, allowing you to disclose only a part of your total order quantity to the market at a time.
*   **`tag` (str, Optional):** A user-defined tag (up to a certain length, e.g., 8 characters for Zerodha via Kite API) that you can associate with an order for your own tracking or analysis.

**Example of Creating an `Order` Object:**

```python
# Example: A limit buy order for Infosys equity
limit_buy_order = Order(
    symbol="INFY-EQ",
    quantity=10,
    side="BUY",
    order_type="LIMIT",
    product="CNC",
    exchange="NSE",
    price=1450.50,
    tag="MyInvst" # Optional tag
)

# Example: A stop-loss market sell order for Nifty futures
slm_sell_order_futures = Order(
    symbol="NIFTY23AUGFUT", # Replace with current month's future symbol
    quantity=1, # 1 lot
    side="SELL",
    order_type="SL-M",
    product="NRML", # Or MIS if intraday
    exchange="NFO",
    trigger_price=19500.00,
    validity="DAY"
)

print(f"Limit Buy Order: Symbol={limit_buy_order.symbol}, Qty={limit_buy_order.quantity}, Price={limit_buy_order.price}")
print(f"SL-M Sell Order: Symbol={slm_sell_order_futures.symbol}, Qty={slm_sell_order_futures.quantity}, Trigger={slm_sell_order_futures.trigger_price}")
```

Once an `Order` object is created and populated with these attributes, it's ready to be passed to the broker's order placement method, which we'll cover next.

## Placing Orders

After creating an `Order` object, you can place it using the `order_place` method of your authenticated `broker` instance. The general workflow is:

1.  Define your order parameters by creating an `Order` instance.
2.  Call `broker.order_place(order=your_order_object)`.
3.  The broker will attempt to place the order and return a response, typically including an `order_id` if successful.

Let's look at examples for different order types. Assume `broker` is your authenticated `Zerodha` instance from the previous steps, and `Order` has been imported.

### 1. Market Order

A market order executes at the best available price in the market. You don't specify a price.

```python
# Ensure 'broker' is your authenticated Zerodha instance and Order is imported
# from omspy.order import Order

# Conceptual: assume 'broker' is an initialized and authenticated Zerodha broker object
# if 'broker' not in locals() or broker is None:
#     print("Broker not initialized. Please run authentication steps first.")
#     # return # or raise an error

try:
    market_buy_order = Order(
        symbol="RELIANCE-EQ",
        quantity=5,
        side="BUY",
        order_type="MARKET",
        product="MIS",       # Intraday
        exchange="NSE",
        tag="RelMktBuy"
    )

    # response = broker.order_place(order=market_buy_order) # This line would be active in a real script
    # order_id = response.get("order_id")

    # Mocking response for tutorial text
    order_id = "mock_market_order_123"
    response = {"status": "success", "order_id": order_id, "message": "Market order placed (mocked)."}


    if order_id:
        print(f"Market buy order placed successfully for RELIANCE-EQ. Order ID: {order_id}")
        print(f"Full response: {response}")
    else:
        print(f"Market order placement failed or order ID not found in response: {response}")

except Exception as e:
    print(f"Error placing market order: {e}")
```

### 2. Limit Order

A limit order allows you to specify the exact price at which you want to buy or sell. The order will only execute if the market reaches your limit price or better.

```python
# Ensure 'broker' is your authenticated Zerodha instance and Order is imported

try:
    limit_sell_order = Order(
        symbol="INFY-EQ",
        quantity=10,
        side="SELL",
        order_type="LIMIT",
        product="CNC",       # Delivery
        exchange="NSE",
        price=1500.00,       # Your desired selling price or higher
        tag="InfyLimitSell"
    )

    # response = broker.order_place(order=limit_sell_order) # This line would be active
    # order_id = response.get("order_id")

    # Mocking response for tutorial text
    order_id = "mock_limit_order_456"
    response = {"status": "success", "order_id": order_id, "message": "Limit order placed (mocked)."}

    if order_id:
        print(f"Limit sell order placed successfully for INFY-EQ at 1500.00. Order ID: {order_id}")
        print(f"Full response: {response}")
    else:
        print(f"Limit order placement failed or order ID not found in response: {response}")

except Exception as e:
    print(f"Error placing limit order: {e}")
```

### 3. Stop-Loss Limit (SL) Order

An SL order is used to limit potential losses or protect profits. It requires both a `trigger_price` and a `price` (limit price).
*   When the `trigger_price` is hit, a limit order is sent to the exchange at the specified `price`.
*   For a BUY SL order: `trigger_price` is typically above the current market price. You buy when LTP >= `trigger_price`, at your `price` or lower.
*   For a SELL SL order: `trigger_price` is typically below the current market price. You sell when LTP <= `trigger_price`, at your `price` or higher.

```python
# Ensure 'broker' is your authenticated Zerodha instance and Order is imported

try:
    # Example: Protecting a long position in SBIN-EQ
    # If SBIN-EQ drops to 570.00, place a limit order to sell at 569.50
    sl_sell_order = Order(
        symbol="SBIN-EQ",
        quantity=20,
        side="SELL",
        order_type="SL",
        product="CNC",
        exchange="NSE",
        price=569.50,          # Limit price: Sell at this price or higher once triggered
        trigger_price=570.00,  # Trigger price: When LTP hits this, place the limit order
        tag="SbinSLsell"
    )

    # response = broker.order_place(order=sl_sell_order) # This line would be active
    # order_id = response.get("order_id")

    # Mocking response for tutorial text
    order_id = "mock_sl_order_789"
    response = {"status": "success", "order_id": order_id, "message": "SL order placed (mocked)."}

    if order_id:
        print(f"Stop-Loss (SL) sell order placed for SBIN-EQ. Trigger: 570.00, Price: 569.50. Order ID: {order_id}")
        print(f"Full response: {response}")
    else:
        print(f"SL order placement failed or order ID not found in response: {response}")

except Exception as e:
    print(f"Error placing SL order: {e}")
```

### 4. Stop-Loss Market (SL-M) Order

An SL-M order also uses a `trigger_price`. When this price is hit, a market order is sent to the exchange. This increases the likelihood of execution compared to an SL order but does not guarantee the execution price.

```python
# Ensure 'broker' is your authenticated Zerodha instance and Order is imported

try:
    # Example: Buying NIFTY Futures if it breaks out above a certain level
    slm_buy_order_futures = Order(
        symbol="NIFTY23AUGFUT", # Replace with current future symbol
        quantity=1, # 1 lot
        side="BUY",
        order_type="SL-M",
        product="NRML",
        exchange="NFO",
        trigger_price=19800.00, # If LTP hits 19800.00, place a market buy order
        validity="DAY",
        tag="NiftySLMbuy"
    )

    # response = broker.order_place(order=slm_buy_order_futures) # This line would be active
    # order_id = response.get("order_id")

    # Mocking response for tutorial text
    order_id = "mock_slm_order_012"
    response = {"status": "success", "order_id": order_id, "message": "SL-M order placed (mocked)."}

    if order_id:
        print(f"Stop-Loss Market (SL-M) buy order placed for NIFTY Futures. Trigger: 19800.00. Order ID: {order_id}")
        print(f"Full response: {response}")
    else:
        print(f"SL-M order placement failed or order ID not found in response: {response}")

except Exception as e:
    print(f"Error placing SL-M order: {e}")
```

Always check the response from `broker.order_place()` to confirm the order status and retrieve the `order_id`, which is crucial for any subsequent modifications or cancellations. The exact structure of the response dictionary may vary based on `omspy`'s implementation for Zerodha, so inspect it to understand all returned fields.

## Modifying a Pending Order

If you have an open order that has not yet been fully executed, you can often modify some of its parameters. Common modifiable parameters include `price` (for limit orders), `quantity` (though rules may apply, e.g., you usually can't reduce quantity below what's already filled), and `trigger_price` (for stop-loss orders).

You'll need the `order_id` obtained when you first placed the order.

```python
# Assume 'broker' is your authenticated Zerodha instance
# Assume 'existing_order_id' is an ID of a pending order you placed earlier.

existing_order_id = "YOUR_PENDING_ORDER_ID" # Replace with an actual pending order ID for testing

if existing_order_id == "YOUR_PENDING_ORDER_ID":
    print("Please replace 'YOUR_PENDING_ORDER_ID' with an actual ID of a pending order you want to try modifying.")
else:
    try:
        new_price = 1452.00  # New price for a pending limit order
        new_quantity = 12    # New quantity (ensure it's valid for the order state)

        # Example: Modifying price and quantity of a pending limit order
        # Not all parameters can be modified. Check omspy/broker documentation.
        # Common parameters: price, quantity, trigger_price
        # modification_response = broker.order_modify( # This line would be active
        #     order_id=existing_order_id,
        #     price=new_price,
        #     # quantity=new_quantity, # Uncomment to modify quantity
        #     # trigger_price=new_trigger_price # For SL orders
        # )

        # Mocking response for tutorial text
        modification_response = {"status": "success", "order_id": existing_order_id, "message": "Order modified (mocked)."}
        modified_order_id = modification_response.get("order_id")

        if modified_order_id:
            print(f"Order modification request for {existing_order_id} processed. New Order ID (if changed): {modified_order_id}")
            print(f"Full modification response: {modification_response}")
        else:
            print(f"Order modification failed or ID not in response: {modification_response}")

    except Exception as e:
        print(f"Error modifying order {existing_order_id}: {e}")
```
**Note:**
*   You can only modify orders that are still open (pending) on the exchange.
*   Modifying an order might cause it to lose its original position in the exchange queue.
*   The specific parameters that can be modified depend on the broker's rules and the current state of the order.

## Cancelling a Pending Order

You can cancel an open order that has not been fully executed using its `order_id`.

```python
# Assume 'broker' is your authenticated Zerodha instance
# Assume 'order_id_to_cancel' is an ID of a pending order you placed earlier.

order_id_to_cancel = "YOUR_PENDING_ORDER_ID_TO_CANCEL" # Replace with an actual ID

if order_id_to_cancel == "YOUR_PENDING_ORDER_ID_TO_CANCEL":
    print("Please replace 'YOUR_PENDING_ORDER_ID_TO_CANCEL' with an actual ID of a pending order you want to try cancelling.")
else:
    try:
        # cancellation_response = broker.order_cancel(order_id=order_id_to_cancel) # This line would be active

        # Mocking response for tutorial text
        cancellation_response = {"status": "success", "order_id": order_id_to_cancel, "message": "Order cancelled (mocked)."}
        cancelled_order_id = cancellation_response.get("order_id")
        status = cancellation_response.get("status", "UNKNOWN")

        if cancelled_order_id:
            print(f"Order cancellation request for {order_id_to_cancel} processed. Status: {status}")
            print(f"Full cancellation response: {cancellation_response}")
        else:
            print(f"Order cancellation failed or ID not in response: {cancellation_response}")

    except Exception as e:
        print(f"Error cancelling order {order_id_to_cancel}: {e}")
```
**Note:**
*   If an order is already fully executed, it cannot be cancelled.
*   If an order is partially executed, you can usually cancel the remaining unfilled quantity. The executed portion remains as a trade.
*   Always check the response to confirm the cancellation status.

## Fetching Order Information

`omspy` should provide methods to retrieve details about your orders.

### Order Book/History

To get a list of orders (e.g., for the current day or a historical range, depending on `omspy`'s implementation):

```python
# Assume 'broker' is your authenticated Zerodha instance

try:
    # omspy might offer this as a property:
    # orders = broker.orders
    # Or as a method:
    # orders = broker.get_orders() # Assuming a get_orders() method

    # Mocking response for tutorial text
    orders = [
        {"order_id": "mock_order_1", "symbol": "INFY-EQ", "order_type": "LIMIT", "side": "BUY", "quantity": 10, "price": 1450.00, "status": "COMPLETE"},
        {"order_id": "mock_order_2", "symbol": "RELIANCE-EQ", "order_type": "MARKET", "side": "SELL", "quantity": 5, "price": 0, "status": "PENDING"}
    ]

    if orders:
        print(f"Retrieved {len(orders)} order(s):")
        for order_info in orders:
            print(f"  ID: {order_info.get('order_id')}, Symbol: {order_info.get('symbol')}, "
                  f"Type: {order_info.get('order_type')}, Side: {order_info.get('side')}, "
                  f"Qty: {order_info.get('quantity')}, Price: {order_info.get('price')}, "
                  f"Status: {order_info.get('status')}")
    else:
        print("No orders found or an empty list was returned.")

except Exception as e:
    print(f"Error fetching order book/history: {e}")
```

### Status of a Specific Order

To get details for a single order using its `order_id`:

```python
# Assume 'broker' is your authenticated Zerodha instance
target_order_id = "AN_EXISTING_ORDER_ID" # Replace with an actual order ID

if target_order_id == "AN_EXISTING_ORDER_ID":
    print("Please replace 'AN_EXISTING_ORDER_ID' with an actual order ID to fetch its status.")
else:
    try:
        # Method name might be get_order_status() or get_order_history(order_id=...)
        # order_status_details = broker.get_order_status(order_id=target_order_id)

        # Mocking response for tutorial text
        order_status_details = {"order_id": target_order_id, "symbol": "SBIN-EQ", "status": "OPEN", "filled_quantity": 0, "average_price": 0.0}

        if order_status_details:
            print(f"Details for Order ID {target_order_id}:")
            print(f"  Symbol: {order_status_details.get('symbol')}")
            print(f"  Status: {order_status_details.get('status')}")
            print(f"  Filled Quantity: {order_status_details.get('filled_quantity')}")
            print(f"  Average Price: {order_status_details.get('average_price')}")
        else:
            print(f"Could not retrieve status for Order ID {target_order_id}, or no details returned.")

    except Exception as e:
        print(f"Error fetching status for order {target_order_id}: {e}")
```

## Fetching Account Details

`omspy` should also allow you to fetch your current account status.

### Positions

To get your current open positions:

```python
# Assume 'broker' is your authenticated Zerodha instance

try:
    # This might be a property:
    # current_positions = broker.positions
    # Or a method:
    # current_positions = broker.get_positions()

    # Mocking response for tutorial text
    current_positions = {
        "net": [
            {"symbol": "TCS-EQ", "quantity": 5, "average_price": 3200.00, "pnl": 250.00, "ltp": 3250.00},
            {"symbol": "NIFTY23AUGFUT", "quantity": -1, "average_price": 19600.00, "pnl": -500.00, "ltp": 19610.00}
        ],
        "day": [] # Day positions might also be available
    }

    if current_positions:
        print("Current Positions:")
        positions_list = current_positions.get('net', []) if isinstance(current_positions, dict) else current_positions

        if not positions_list:
            print("  No open positions.")
        else:
            for pos in positions_list:
                print(f"  Symbol: {pos.get('symbol')}, Qty: {pos.get('quantity')}, "
                      f"Avg Price: {pos.get('average_price')}, P&L: {pos.get('pnl')}, "
                      f"LTP: {pos.get('ltp')}")
    else:
        print("Could not retrieve positions or no positions held.")

except Exception as e:
    print(f"Error fetching positions: {e}")
```

### Funds / Margins

To get your available funds and margin details:

```python
# Assume 'broker' is your authenticated Zerodha instance

try:
    # This might be a property:
    # funds_info = broker.funds
    # Or a method:
    # funds_info = broker.get_funds()

    # Mocking response for tutorial text
    funds_info = {
        "equity": {"available_margin": 100000.00, "used_margin": 25000.00, "payin": 0.0},
        "commodity": {"available_margin": 50000.00, "used_margin": 5000.00}
    }

    if funds_info:
        print("Funds & Margin Information:")
        equity_margins = funds_info.get('equity', {})
        commodity_margins = funds_info.get('commodity', {})

        if equity_margins:
            print(f"  Equity Available Margin: {equity_margins.get('available_margin')}")
            print(f"  Equity Used Margin: {equity_margins.get('used_margin')}")
        if commodity_margins:
            print(f"  Commodity Available Margin: {commodity_margins.get('available_margin')}")
            print(f"  Commodity Used Margin: {commodity_margins.get('used_margin')}")
    else:
        print("Could not retrieve funds information.")

except Exception as e:
    print(f"Error fetching funds: {e}")
```

## Getting Market Quotes

To fetch live market data for an instrument (symbol).

```python
# Assume 'broker' is your authenticated Zerodha instance

try:
    # The method signature might vary.
    # quote = broker.quote(symbol="INFY-EQ", exchange="NSE")

    # Mocking response for tutorial text
    quote = {
        "symbol": "INFY-EQ", "ltp": 1480.50,
        "ohlc": {"open": 1470.00, "high": 1485.00, "low": 1465.00, "close": 1468.00},
        "volume": 1234567, "change": 12.50
    }

    if quote:
        print(f"Quote for INFY-EQ on NSE:")
        print(f"  LTP: {quote.get('ltp')}")
        print(f"  Open: {quote.get('ohlc', {}).get('open')}")
        print(f"  High: {quote.get('ohlc', {}).get('high')}")
        print(f"  Low: {quote.get('ohlc', {}).get('low')}")
        print(f"  Close: {quote.get('ohlc', {}).get('close')}")
        print(f"  Volume: {quote.get('volume')}")
        print(f"  Change: {quote.get('change')}")
    else:
        print("Could not retrieve quote for INFY-EQ.")

except Exception as e:
    print(f"Error fetching quote: {e}")
```
**Note:** The exact structure of the data returned by these methods (`orders`, `positions`, `funds`, `quote`) will depend on `omspy`'s specific implementation for the Zerodha broker. Always inspect the returned data to understand its format and available fields.

## Basic Error Handling

When interacting with broker APIs, errors are common due to various reasons like network issues, invalid inputs, insufficient funds, API rate limits, or broker-side rejections. `omspy` will likely communicate these errors by raising Python exceptions.

It's crucial to wrap your `omspy` calls in `try...except` blocks to handle potential issues gracefully.

```python
# Assume 'broker' is your authenticated Zerodha instance
# from omspy.order import Order
# from omspy.exceptions import APIError, OrderException, AuthenticationError # Hypothetical exceptions

try:
    # Example: Attempting to place an order
    order_to_place = Order(
        symbol="NONEXISTENT-EQ", # Potentially invalid symbol
        quantity=1,
        side="BUY",
        order_type="MARKET",
        product="MIS",
        exchange="NSE"
    )
    # response = broker.order_place(order=order_to_place) # This line would be active
    # Mocking response for tutorial text
    response = {"status": "error", "message": "Invalid symbol (mocked)."}
    print(f"Order placement response: {response}")

# It's good practice to catch specific exceptions if omspy defines them
# except AuthenticationError as e:
#     print(f"Authentication Error: {e}. Check your credentials or session.")
# except OrderException as e:
#     print(f"Order Placement Error: {e}. The order might have been rejected by the broker.")
# except APIError as e:
#     print(f"Broker API Error: {e}. There might be an issue with the API itself.")
except Exception as e: # Catch-all for other unexpected errors
    print(f"An unexpected error occurred: {e}")
    # In a real application, you would log this error in more detail.
```

**Key things to consider for error handling:**

*   **Specific Exceptions:** Check the `omspy` documentation for any custom exceptions it raises (e.g., for authentication failures, order placement issues, API errors). Catching these specific exceptions allows for more targeted error handling.
*   **Response Inspection:** Even if an API call doesn't raise an exception, the response from the broker might contain error messages or indicate failure. Always inspect the response content.
*   **Logging:** For any application beyond simple scripts, implement robust logging to record errors, API requests, and responses. This is invaluable for debugging.
*   **Retries:** For transient errors like network issues, you might implement a retry mechanism with exponential backoff, but be careful with operations that are not idempotent (like order placement without a unique client order ID).

## Conclusion

This tutorial has covered the fundamental steps to get started with `omspy` for interacting with your Zerodha account. You've learned how to:

*   Install and set up `omspy`.
*   Authenticate with Zerodha.
*   Define and place various types of orders (Market, Limit, SL, SL-M).
*   Modify and cancel your pending orders.
*   Retrieve your order history, positions, funds, and market quotes.
*   Think about basic error handling.

`omspy` aims to simplify these interactions. As a next step, you should consult the **official `omspy` documentation** for more advanced features, detailed information on all available methods, parameters, response structures, and specific error handling strategies.

Remember to trade responsibly and test any trading automation thoroughly in a simulated environment or with very small amounts before committing significant capital. Happy coding and trading!

```
