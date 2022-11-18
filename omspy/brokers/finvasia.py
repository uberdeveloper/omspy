from omspy.brokers.api_helper import ShoonyaApiPy
from omspy.base import Broker, pre, post
from typing import Optional, List, Dict, Union
import pendulum
import pyotp
import logging


class Finvasia(Broker):
    """
    Automated Trading class
    """

    def __init__(
        self,
        user_id: str,
        password: str,
        pin: str,
        vendor_code: str,
        app_key: str,
        imei: str,
    ):
        self._user_id = user_id
        self._password = password
        self._pin = pin
        self._vendor_code = vendor_code
        self._app_key = app_key
        self._imei = imei
        self.finvasia = ShoonyaApiPy()
        super(Finvasia, self).__init__()

    def login(self) -> Union[Dict, None]:
        return self.finvasia.login(
            userid=self._user_id,
            password=self._password,
            twoFA=pyotp.TOTP(self._pin).now(),
            vendor_code=self._vendor_code,
            api_secret=self._app_key,
            imei=self._imei,
        )

    def authenticate(self) -> Union[Dict, None]:
        """
        Authenticate the user
        """
        return self.login()

    def _convert_symbol(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Convert raw symbol to finvasia
        """
        if symbol.endswith("-EQ") or symbol.endswith("-eq"):
            return symbol
        else:
            return f"{symbol}-EQ"

    @property
    @post
    def orders(self) -> List[Dict]:
        orderbook = self.finvasia.get_order_book()
        if len(orderbook) == 0:
            return orderbook

        order_list = []
        float_cols = ["avgprc", "prc", "rprc", "trgprc"]
        int_cols = ["fillshares", "qty"]
        for order in orderbook:
            try:
                for int_col in int_cols:
                    order[int_col] = int(order.get(int_col, 0))
                for float_col in float_cols:
                    order[float_col] = float(order.get(float_col, 0))
                ts = order["exch_tm"]
                order["exchange_timestamp"] = pendulum.from_format(
                    ts, fmt="DD-MM-YYYY HH:mm:ss", tz="Asia/Kolkata"
                )
                ts2 = order["norentm"]
                order["broker_timestamp"] = pendulum.from_format(
                    ts2, fmt="HH:mm:ss DD-MM-YYYY", tz="Asia/Kolkata"
                )
            except Exception as e:
                logging.error(e)
            order_list.append(order)
        return order_list

    @property
    @post
    def positions(self) -> List[Dict]:
        positionbook = self.finvasia.get_positions()
        if len(positionbook) == 0:
            return positionbook

        position_list = []
        int_cols = ["netqty", "daybuyqty", "daysellqty"]
        float_cols = ["daybuyamt", "daysellamt"]
        for position in positionbook:
            try:
                for int_col in int_cols:
                    position[int_col] = int(position.get(int_col, 0))
                for float_col in float_cols:
                    position[float_col] = float(position.get(float_col, 0))
            except Exception as e:
                logging.error(e)
            position_list.append(position)
        return position_list

    @property
    @post
    def trades(self) -> List[Dict]:
        tradebook = self.finvasia.get_trade_book()
        if len(tradebook) == 0:
            return tradebook

        trade_list = []
        int_cols = ["flqty", "qty", "fillshares"]
        float_cols = ["prc", "flprc"]
        for trade in tradebook:
            try:
                for int_col in int_cols:
                    trade[int_col] = int(trade.get(int_col, 0))
                for float_col in float_cols:
                    trade[float_col] = float(trade.get(float_col, 0))
            except Exception as e:
                logging.error(e)
            trade_list.append(trade)
        return trade_list

    def get_order_type(self, order_type: str) -> str:
        """
        Convert a generic order type to this specific
        broker's order type string
        returns MKT if the order_type is not matching
        """
        order_types = dict(
            LIMIT="LMT", MARKET="MKT", SL="SL-LMT", SLM="SL-MKT", SLL="SL-LMT"
        )
        order_types["SL-M"] = "SL-MKT"
        order_types["SL-L"] = "SL-LMT"
        return order_types.get(order_type.upper(), "MKT")

    @pre
    def order_place(self, **kwargs) -> Union[str, None]:
        symbol = kwargs.pop("symbol")
        symbol = self._convert_symbol(symbol)
        side = kwargs.pop("side")
        order_type = kwargs.pop("order_type", "MKT")
        if order_type:
            order_type = self.get_order_type(order_type)
        if side:
            side = side.upper()[0]
        if symbol:
            symbol = symbol.upper()
        order_args = dict(
            tradingsymbol=symbol,
            buy_or_sell=side,
            price_type=order_type,
            exchange="NSE",
            retention="DAY",
            product_type="I",
            discloseqty=0,
        )
        order_args.update(kwargs)
        return self.finvasia.place_order(**order_args)

    def order_cancel(self, order_id: str) -> Union[Dict, None]:
        """
        Cancel an existing order
        """
        return self.finvasia.cancel_order(orderno=order_id)

    @pre
    def order_modify(self, **kwargs) -> Union[str, None]:
        """
        Modify an existing order
        """
        symbol = kwargs.pop("tradingsymbol")
        order_id = kwargs.pop("order_id", None)
        order_type = kwargs.pop("order_type", "MKT")
        if order_type:
            order_type = self.get_order_type(order_type)
        if symbol:
            symbol = self._convert_symbol(symbol).upper()
        order_args = dict(
            orderno=order_id,
            newprice_type=order_type,
            exchange="NSE",
            tradingsymbol=symbol,
        )
        order_args.update(kwargs)
        return self.finvasia.modify_order(**order_args)
