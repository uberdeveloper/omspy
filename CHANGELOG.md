## 0.2.0

### Features
* `Order, CompoundOrder` models changed from dataclass to pydantic models
* database class changed to sqlite_utils from native python sqlite3 for better reading and writing, connection now returns `sqlite_utils.Database` instead of `sqlite3.Connection`.
* #3 `Order` could now be directly added using the `add` method and this inherits the sqlite3 database from the compound order if no connection is specified
* #8 save method added to save orders to database in bulk

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
