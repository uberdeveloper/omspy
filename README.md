# 📈 OMSpy Order Management

A powerful yet simple order management system for trading operations. Build, track, and execute orders with confidence.

## ✨ Features

- 🎯 **Simple API** - Intuitive order creation and management
- 📊 **Position Tracking** - Real-time position and P&L monitoring
- 💾 **Database Integration** - Built-in SQLite persistence
- 🔄 **Order Types** - Market, Limit, Stop, and complex orders
- 📦 **Order Baskets** - Group and manage multiple orders
- ⚡ **High Performance** - Optimized for trading workflows

## 🚀 Quick Start

### 🎯 Create a Basic Order

```python
from omspy.order import Order

# Create a simple market buy order
order = Order(symbol="AAPL", side="buy", quantity=10)
print(f"Order ID: {order.id}")
```

### 💰 Create Different Order Types

```python
# Market order (executes immediately)
market_order = Order(symbol="TSLA", side="buy", quantity=5)

# Limit order (executes at specific price or better)
limit_order = Order(symbol="MSFT", side="sell", quantity=3,
                    order_type="LIMIT", price=380.50)

# Stop loss order (triggers when price drops)
stop_order = Order(symbol="NVDA", side="sell", quantity=2,
                   order_type="STOP", trigger_price=450.00)
```

### ⏰ Time-Based Orders

```python
# Order that expires after 30 minutes
short_order = Order(symbol="GOOGL", side="buy", quantity=1,
                    expires_in=1800)  # 30 minutes

# Day order (valid until market close)
day_order = Order(symbol="META", side="buy", quantity=5,
                  validity="DAY")
```

### 🔄 Order Operations

```python
# Execute order through broker
order_id = order.execute(broker=my_broker)
if order_id:
    print(f"📋 Order placed with ID: {order_id}")

# Update order from exchange feed
exchange_data = {
    "status": "PARTIALLY_FILLED",
    "filled_quantity": 5,
    "average_price": 175.25
}
order.update(exchange_data)

# Modify existing order
order.modify(broker=my_broker, quantity=8, price=174.50)

# Cancel pending order
if order.is_pending:
    order.cancel(broker=my_broker)
```

### 📋 Clone and Modify Orders

```python
# Create a template order
template = Order(symbol="AAPL", side="buy", quantity=10,
                 order_type="LIMIT", price=150.00)

# Clone for different symbols/dates
buy_googl = template.clone()
buy_googl.symbol = "GOOGL"
buy_googl.price = 125.50

sell_msft = template.clone()
sell_msft.symbol = "MSFT"
sell_msft.side = "sell"
sell_msft.price = 380.25
```

## 📦 Order Baskets (CompoundOrder)

### 🎯 Create Order Basket

```python
from omspy.order import CompoundOrder

# Create a basket for strategy execution
basket = CompoundOrder(broker=my_broker)

# Add multiple orders
basket.add_order(symbol="AAPL", side="buy", quantity=10)
basket.add_order(symbol="MSFT", side="sell", quantity=5)
basket.add_order(symbol="TSLA", side="buy", quantity=3,
                 order_type="LIMIT", price=250.00)
```

### 📊 Track Basket Positions

```python
# Get net positions across all orders
positions = basket.positions
print(f"📊 Net positions: {dict(positions)}")

# Get total quantities
print(f"Buy quantities: {dict(basket.buy_quantity)}")
print(f"Sell quantities: {dict(basket.sell_quantity)}")
```

### 💰 Calculate Average Prices

```python
# Get average buy/sell prices per symbol
avg_buy = basket.average_buy_price
avg_sell = basket.average_sell_price

print(f"📈 Average buy prices: {avg_buy}")
print(f"📉 Average sell prices: {avg_sell}")
```

### ⚡ Execute Basket Operations

```python
# Execute all orders in basket
basket.execute_all()

# Update all pending orders with exchange data
order_updates = {
    "order_123": {"status": "COMPLETE", "filled_quantity": 10},
    "order_456": {"status": "PARTIALLY_FILLED", "filled_quantity": 3}
}
results = basket.update_orders(order_updates)
print(f"Update results: {results}")

# Check completed vs pending orders
completed = basket.completed_orders
pending = basket.pending_orders
print(f"✅ Completed: {len(completed)} orders")
print(f"⏳ Pending: {len(pending)} orders")
```

### 🎯 Advanced Basket Management

```python
# Access orders by index or custom key
order_by_index = basket.get(0)  # First order
order_by_key = basket.get("aapl_buy")  # Custom key if set

# Add orders with custom keys
basket.add_order(symbol="NVDA", side="buy", quantity=2, key="nvidia_entry")

# Calculate total MTM with live prices
basket.update_ltp({
    "AAPL": 175.50,
    "MSFT": 380.25,
    "TSLA": 252.00
})
print(f"💰 Total P&L: ${basket.total_mtm:.2f}")
```

## 💾 Database Integration

### 🔧 Enable Database Storage

```python
from omspy.order import create_db

# Create persistent database
db = create_db("trading_orders.db")

# Auto-save orders to database
order.connection = db
basket.connection = db  # All orders in basket will save
```

### 💾 Manual Database Operations

```python
# Save specific order
success = order.save_to_db()
print(f"Order saved: {success}")

# Save all orders in basket
basket.save()

# Query orders from database
for row in db["orders"].rows:
    print(f"ID: {row['id']}, Symbol: {row['symbol']}, Status: {row['status']}")
```

## ⏰ Order Lifecycle Management

### 🕐 Time and Expiration

```python
# Check time until expiry
time_left = order.time_to_expiry
print(f"⏰ Expires in: {time_left} seconds")

# Check if order has expired
if order.has_expired:
    print("⏰ Order has expired")

# Time since expiry (if expired)
if order.has_expired:
    time_expired = order.time_after_expiry
    print(f"⏰ Expired {time_expired} seconds ago")
```

### 🔒 Order Locking

```python
# Prevent order modifications for 60 seconds
order.add_lock(code=1, seconds=60)  # 1 = modify lock

# Prevent order cancellation for 30 seconds
order.add_lock(code=2, seconds=30)  # 2 = cancel lock

# Check lock status
if not order.lock.can_modify:
    print(f"🔒 Modify locked until {order.lock.modification_lock_till}")
```

## 🎯 Order Management Patterns

### 📋 Scalping Strategy

```python
# Quick entries and exits
scalp = CompoundOrder(broker=broker)

# Enter position
scalp.add_order(symbol="AAPL", side="buy", quantity=100,
                order_type="MARKET", key="entry")

# Set stop loss
scalp.add_order(symbol="AAPL", side="sell", quantity=100,
                order_type="STOP", trigger_price=174.00, key="stop_loss")

# Set profit target
scalp.add_order(symbol="AAPL", side="sell", quantity=100,
                order_type="LIMIT", price=176.00, key="profit_target")
```

### 📊 Pair Trading

```python
# Trade two correlated instruments
pair_trade = CompoundOrder(broker=broker)

# Long first instrument
pair_trade.add_order(symbol="XOM", side="buy", quantity=50, key="long_leg")

# Short second instrument (ratio adjusted)
pair_trade.add_order(symbol="CVX", side="sell", quantity=45, key="short_leg")

# Monitor pair performance
positions = pair_trade.positions
correlation_exposure = positions.get("XOM", 0) + positions.get("CVX", 0)
print(f"📊 Net pair exposure: {correlation_exposure}")
```

### 🔄 Bracket Orders

```python
# Create complete bracket in one basket
bracket = CompoundOrder(broker=broker)

# Main entry order
bracket.add_order(symbol="TSLA", side="buy", quantity=10,
                  order_type="LIMIT", price=250.00, key="entry")

# Profit target (OCA - One Cancels All would be nice addition)
bracket.add_order(symbol="TSLA", side="sell", quantity=10,
                  order_type="LIMIT", price=275.00, key="profit_target")

# Stop loss
bracket.add_order(symbol="TSLA", side="sell", quantity=10,
                  order_type="STOP", trigger_price=240.00, key="stop_loss")
```

## 🛠️ Best Practices

### ✅ Order Management
- Always validate order parameters before execution
- Use appropriate order types for your strategy
- Set reasonable expiration times
- Monitor order status regularly
- Implement proper error handling

### 📊 Position Management
- Track net positions across all orders
- Use CompoundOrder for multi-leg strategies
- Calculate and monitor P&L regularly
- Set stop losses and profit targets
- Consider position sizing rules

### 💾 Data Management
- Enable database persistence for recovery
- Save orders after important state changes
- Regularly backup trading databases
- Use meaningful order identifiers
- Log important order events

## 📋 Requirements

- **Python 3.11+**
- **pydantic** - Data validation and serialization
- **pendulum** - Advanced datetime handling
- **sqlite-utils** - Database operations
- **numpy (<2.0.0)** - Numerical computations

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/your-org/omspy.git
cd omspy

# Install dependencies with poetry
poetry install

# Activate virtual environment
poetry shell
```

## 📚 Examples

The `examples/` directory contains complete working examples:

- `basic_order.py` - Simple order creation and execution
- `basket_trading.py` - Multi-order strategies
- `database_integration.py` - Persistent order storage
- `option_strategies.py` - Options trading workflows

---

## 💡 About OMSpy

OMspy is a **broker-agnostic order management system** with a common API, advanced order types, and comprehensive trading workflow support. Built for traders who need reliability, flexibility, and simplicity in their order management.

**Key Features:**
- 🔄 **Broker Agnostic** - Works with multiple brokers through common API
- 🎯 **Advanced Orders** - Support for complex order types and strategies
- 📊 **Real-time Tracking** - Position monitoring and P&L calculation
- 💾 **Persistent Storage** - Database-backed order management
- ⚡ **High Performance** - Optimized for active trading environments
