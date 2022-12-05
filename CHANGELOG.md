### 0.10.0
### Features
* order `execute, modify, cancel` functions to take additional attribs_to_copy argument to copy attributes from brokers
* Broker instance could have now have properties to be added automatically during `execute, modify, cancel` function

### Fixes
* Finvasia broker to return order_id as a string instead of dictionary
* Finvasia broker `order_modify` to correctly add arguments when called

### 0.9.1
### Fixes
* Finvasia broker to suffix EQ to orders only when the exchange is NSE
### Improvement
* Finvasia broker - more columns converted to proper types
* Kotak broker - more columns converted
### Internals
* Kotak broker `create_instrument_master` to fetch dataframe from a different function, the new function is added for better modularity

## 0.9.0
### Features
* `TrailingStopOrder` added to stop orders
* `TargetOrder` added to stop orders
* `BracketOrder` removed from stop orders

### Improvements
* `StopOrder` and `StopLimitOrder` model changed

### Fixes
* Kotak broker exchange_timestamp format handled correctly
* Finvasia broker exchange and broker timestamp format handled correctly
* Timestamp for kotak, finvasia brokers to be saved in db in expected format

## 0.8.3
### Features
* `close_all_positions` could take a symbol_transformer function to transform symbols
* `close_all_positions` can take positions as an optional argument; this would help in passing select positions to square off instead of closing all positions
* `PegExisting` and `PeqSequential` can now take `modify_args` to add any extra broker arguments needed when modifying orders

### Improvements
* `close_all_positions` to handle errors and valid quantity of any type
* type conversion done for data received from broker `Finvasia`
* #9 when an `Order` is added to `CompoundOrder` add an id automatically if there is no id
* #25 `PegSequential` order lock mechanism now dependent on `add_lock` method for each order; so each order could have its own order lock.

### Fixes
* #15 do not update `Order` if order `is_done` (completed/rejected/canceled)

### Internals
* tests improved for `Order` class


## 0.8.2
### Improvements
* Instrument master for broker `kotak` could be generated for any combination of columns
* `modify` order could now take extra attributes to be passed on to broker
* tests rewritten with `PurePath` and other refactoring, credits to @soumyarai2050 for pushing these changes

### Fixes
* Instrument master for  broker `kotak` to handle strike prices till 3 decimal places (for currency strikes)
* `modify_order` for broker `kotak` to correctly handle order types, especially MARKET

## 0.8.1
### Improvements
* TOTP authentication added to Finvasia broker
* TOTP autentication added to MasterTrust broker

## 0.8.0
### Features
* New `OrderStrategy` class added, an abstraction over CompoundOrder
* OrderLock mechanism added to `Order` so that each order would have its own unique lock

## 0.7.1
This is a bug-fix version and enhancement version

### Fixes
* #20 You can now pass order arguments to `PegExisting` and `PegSequential`
* #18 timezone to default to local instead of UTC
* #11 pending quantity to be automatically updated

## 0.7.0
### Features
* CandleStick class added to models
* Cancel subsequent orders in `PegSequential` if one of the orders fail

### Improvements
* `is_done` method added to `Order` - returns True when the order is either complete or canceled or rejected.
* cancel peg orders after expiry

### Fixes
* `order_cancel` not to be called when no  order_id is None

## 0.6.1
### Improvements
* Extra order mappings for SLM and SLL added to finvasia broker
* `order_type` argument resolved for kotak broker

## 0.6.0
### Features
* Broker support added for **finvasia**
* New order type `PegSequential` added to peg orders in sequence

## 0.5.1
### Improvements
* Order Lock mechanism added
* ExistingPeg to check for time expiry before next peg

## 0.5.0
### Features
* ExistingPeg order added to peg existing orders

### Features
* Broker support added for **kotak**

## 0.4.0

### Features
* **BREAKING CHANGE:** Database structured changed. New keys added
* new **multi** module added for placing the same order for multiple clients

### Fixes
* #13 do not change existing timestamp fixed
* cloning an order creates a new timestamp instead of the original one
* keyword arguments passed to `modify` method to update order attributes and then modify the broker order
* peg order attributes carried to child orders

## 0.3.0

### Features
* new **peg order module** added for peg orders.
* peg to market order added with basic arguments
* new **models** module added. This contains basic model for converting and manipulating data
* new **utils** module added that contains utility and helper functions. Functions added
	* create_basic_positions_from_orders_dict
	* dict_filter
	* tick
	* stop_loss_step_decimal
* mandatory arguments for order placement for zerodha broker added. `order_place, order_modify, order_cancel` would now add default arguments for the broker automatically (such as variety);you could override them with kwargs.
* cover_orders function added to broker class, this checks for all valid orders and place stop loss in case of non-matching orders


## 0.2.0

### Features
* **BREAKING CHANGE:** Database model changed
* `Order, CompoundOrder` models changed from dataclass to pydantic models
* database class changed to sqlite_utils from native python sqlite3 for better reading and writing, connection now returns `sqlite_utils.Database` instead of `sqlite3.Connection`.
* #3 `Order` could now be directly added using the `add` method and this inherits the sqlite3 database from the compound order if no connection is specified
* #8 save method added to save orders to database in bulk
* #6 maximum limit for modifications to an order added

### Fixes
* close_all_positions bug fixed by changing status to upper case and including canceled and rejected orders in completed orders
* cancel_all_orders do not cancel already completed orders

### Internals

* `_attrs` now made part of model instead of a property
* tests updated to reflect the new database type


## 0.1.4
* modify order to accept any parameter

## 0.1.3
* save to database on execution

## 0.1.2
* fixes in brokers
* order arguments during execution in compound orders

## 0.1.1
* database support for saving orders added
