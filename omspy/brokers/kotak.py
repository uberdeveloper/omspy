from omspy.base import Broker, pre, post
from typing import Optional, List, Dict, Union
from ks_api_client import ks_api
import pendulum
import pandas as pd
import logging
from copy import deepcopy


def get_url(segment: Optional[str] = "cash") -> str:
    dt = pendulum.now(tz="Asia/Kolkata")
    date_string = dt.strftime("%d_%m_%Y")
    dct = {"cash": "Cash", "fno": "FNO"}
    seg = dct.get(segment, "Cash")
    url = f"https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_{seg}_{date_string}.txt"
    return url


def get_name_for_cash_symbol(
    instrument_name: str, instrument_type: Optional[str] = None
):
    """
    Get the broker interface name for a symbol in cash segment
    """
    if instrument_type is None:
        pass
    elif pd.isna(instrument_type):
        instrument_type = None
    elif not (instrument_type.isalnum()):
        instrument_type = None
    elif instrument_type.upper() == "EQ":
        instrument_type = None
    elif instrument_type.lower() in ("na", "nan"):
        instrument_type = None

    if instrument_type is None:
        return instrument_name
    else:
        return f"{instrument_name}-{instrument_type or False}"


def get_name_for_fno_symbol(
    instrument_name: str,
    expiry: Union[pendulum.Date, pendulum.DateTime, str],
    option_type: Optional[str] = None,
    strike: Optional[Union[float, int]] = None,
):
    """
    Get the broker interface name for a future or option symbol
    Note
    -----
    1)If either the option type or option strike argument is not given, it is considered a futures contract
    2) A contract is considered an option contract only if both option type and strike price is provided
    """
    if isinstance(expiry, str):
        expiry = pendulum.parse(expiry)
    expiry = expiry.strftime("%d%b%y").upper()

    # Set the option type
    opts = {"ce": "call", "pe": "put"}
    if option_type is None:
        option_type = None
    elif pd.isna(option_type):
        option_type = None
    elif not (isinstance(option_type, str)):
        option_type = None
    elif option_type.lower() not in ("ce", "pe"):
        option_type = None
    else:
        option_type = opts.get(option_type.lower())

    # Set the strike
    if strike is None:
        strike = None
    elif not (isinstance(strike, (int, float))):
        strike = None
    elif strike <= 0:
        strike = None

    # Consider an instrument futures if there is no
    # corresponding strike or option type
    if (option_type is None) or (strike is None):
        return f"{instrument_name}{expiry}FUT".upper()
    else:
        return f"{instrument_name}{expiry}{strike}{option_type}".upper()


def convert_strike(strike: Union[int, float]) -> Union[int, float]:
    """
    Convert the type of the strike to an integer if it is an integer or float to 2 points if it is a float
    Note
    ----
    This is only a type conversion
    """
    if (strike - int(strike)) == 0:
        return int(strike)
    else:
        return round(strike, 3)


def download_file(url: str) -> pd.DataFrame:
    """
    Given a url, download the file, parse contents
    and return a dataframe.
    returns an empty Dataframe in case of an error
    """
    try:
        df = pd.read_csv(url, delimiter="|", parse_dates=["expiry"])
        df = df.rename(columns=lambda x: x.lower())
        return df.drop_duplicates(subset=["instrumenttoken"])
    except Exception as e:
        logging.error(e)
        return pd.DataFrame()


def add_name(data, segment: Optional[str] = "cash") -> pd.DataFrame:
    """
    add name to the given dataframe and return it
    tdata
        dataframe with the instrument data
    segment
        segment to add name to either cash or fno
    Note
    -----
    1) The extra column added is inst_name
    """
    if segment.lower() == "cash":
        data["inst_name"] = [
            f"{k}:{get_name_for_cash_symbol(x,y)}"
            for x, y, k in zip(
                data.instrumentname.values,
                data.instrumenttype.values,
                data.exchange.values,
            )
        ]
        return data
    elif segment.lower() == "fno":
        data["inst_name"] = [
            f"{k}:{get_name_for_fno_symbol(a,str(b),c,convert_strike(d))}"
            for a, b, c, d, k in zip(
                data.instrumentname.values,
                data.expiry.values,
                data.optiontype.values,
                data.strike.values,
                data.exchange.values,
            )
        ]
        return data
    else:
        return data


def create_instrument_master(
    name: str = "inst_name", token: str = "instrumenttoken"
) -> Dict[str, int]:
    """
    Create the instrument master
    name
        column name representing the symbol column
    token
        column name representing the token
    Note
    ----
    Takes no arguments by default and returns the entire instrument_master as a dictionary with key as name and values as instrument token
    """
    # TODO: Handle error in case of no instruments
    cash = download_file(get_url(segment="cash"))
    fno = download_file(get_url(segment="fno"))
    cash = add_name(cash, segment="cash")
    fno = add_name(fno, segment="fno")
    df = pd.concat([cash, fno]).drop_duplicates(subset=["instrumenttoken"])
    return {k: int(v) for k, v in zip(df[name].values, df[token].values)}


class Kotak(Broker):
    """
    Automated Trading class
    """

    def __init__(
        self,
        access_token: str,
        userid: str,
        password: str,
        consumer_key: str,
        access_code: Optional[str] = None,
        instrument_master: Optional[str] = None,
        ip: str = "127.0.0.1",
        app_id: str = "default",
    ):
        self._access_token = access_token
        self._userid = userid
        self._password = password
        self._consumer_key = consumer_key
        self._access_code = access_code
        self._ip = ip
        self._app_id = app_id
        if instrument_master is None:
            self.master = create_instrument_master()
        else:
            self.master = instrument_master
        self._rev_master = {v: k for k, v in self.master.items()}
        super(Kotak, self).__init__()

    def get_instrument_token(self, instrument: str) -> Union[int, None]:
        return self.master.get(instrument)

    def _response(self, response: Dict) -> Union[Dict, None]:
        """
        return the response if success key is found else
        return None
        """
        if "Success" in response:
            return response["Success"]
        elif "success" in response:
            return response["success"]
        else:
            return None

    def _get_order_id(self, response: Optional[Dict] = None) -> Union[int, None]:
        """
        return order id from response
        """
        if response is None:
            return None
        elif isinstance(response, dict):
            response = self._response(response)
            if response is None:
                return None
            else:
                return dict(*response.values())["orderId"]
        else:
            return None

    def authenticate(self) -> None:
        try:
            client = ks_api.KSTradeApi(
                access_token=self._access_token,
                userid=self._userid,
                consumer_key=self._consumer_key,
                ip=self._ip,
                app_id=self._app_id,
            )
            client.login(password=self._password)
            client.session_2fa(access_code=self._access_code)
            self.client = client
        except Exception as e:
            logging.error(e)
            self.client = None

    def get_status(self, status: str) -> str:
        """
        Get the order status
        """
        status_map = dict(
            TRAD="COMPLETE",
            CAN="CANCELED",
            OPN="PENDING",
            SLO="PENDING",
            NEWF="PENDING",
        )
        return status_map.get(status.upper(), "PENDING")

    @property
    @post
    def orders(self) -> List[Dict]:
        """
        Return the orders for the day
        """
        order_report = self.client.order_report()
        if "success" in order_report:
            for order in order_report["success"]:
                order["symbol"] = self._rev_master.get(
                    order["instrumentToken"], order["instrumentName"]
                )
                order["status"] = self.get_status(order["status"])
                try:
                    ts = order["orderTimestamp"]
                    ts2 = ts[:-6] + ts[-2:]
                    order["exchange_timestamp"] = pendulum.parse(
                        ts2, tz="Asia/Kolkata", strict=False
                    )
                except Exception as e:
                    logging.error(e)
            return order_report["success"]
        else:
            return order_report

    @property
    @post
    def positions(self) -> List[Dict]:
        """
        Return the positions only for the day
        """
        positions_report = self.client.positions(position_type="TODAYS")
        if "Success" in positions_report:
            for position in positions_report["Success"]:
                position["symbol"] = self._rev_master.get(
                    position["instrumentToken"], position["instrumentName"]
                )
            return positions_report["Success"]
        else:
            return positions_report

    def trades(self) -> List[Dict]:
        pass

    def _get_order_type(self) -> Dict:
        pass

    @pre
    def order_place(
        self, symbol: str, side: str, exchange: str = "NSE", quantity: int = 1, **kwargs
    ) -> Union[str, None]:
        try:
            order_args = dict(
                variety="REGULAR", validity="GFD", order_type="MIS", price=0
            )
            token = self.get_instrument_token(f"{exchange}:{symbol}".upper())
            if not (token):
                logging.warning("No token for this symbol,check your symbol")
                return
            order_args.update(
                dict(
                    transaction_type=side.upper(),
                    instrument_token=token,
                    quantity=quantity,
                )
            )
            order_args.update(kwargs)
            response = self.client.place_order(**order_args)
            return self._get_order_id(response)
        except Exception as e:
            logging.error(e)
            return None

    def order_cancel(self, order_id: str) -> Dict:
        """
        Cancel an existing order
        """
        try:
            order_id = str(order_id)
            response = self.client.cancel_order(order_id=order_id)
            return self._get_order_id(response)
        except Exception as e:
            logging.error(e)
            return None

    def order_modify(self, order_id: str, **kwargs) -> Union[str, None]:
        """
        Modify an order
        """
        try:
            order_type = kwargs.get("order_type")
            if order_type:
                kwargs.pop("order_type")
                if order_type == "MARKET":
                    kwargs["price"] = 0
            order_id = str(order_id)
            response = self.client.modify_order(order_id=order_id, **kwargs)
            response = self._response(response)
            return self._get_order_id(response)
        except Exception as e:
            logging.error(e)
            return None
