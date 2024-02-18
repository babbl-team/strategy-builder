
from bson import ObjectId
from bson.errors import InvalidId
import datetime
from enum import Enum
import json
import numpy as np
from pydantic import BaseModel, validator
import pytz
from typing import (
    List, Union, Optional, 
    Generic, TypeVar, Literal
)
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


# JSON encoder for datetime objs
class JSONEncoder_dt(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return datetime_to_isostr(obj)
        return json.JSONEncoder.default(self, obj)
    

#######################################
###  [ Pydantic Helper Functions ]  ###

def convert_to_utc_datetime(dt_obj: datetime.datetime) -> datetime.datetime:
    return dt_obj.astimezone(tz=pytz.utc)

def datetime_to_utc_date(dt_obj: datetime.datetime) -> datetime.datetime:
    # Converts datetime into UTC datetime, then clamps to date but leaves as datetime
    utc_datetime = dt_obj.astimezone(tz=pytz.utc)
    utc_date = utc_datetime.date()
    out_datetime = datetime.datetime.combine(date=utc_date, time=datetime.time(0, 0, 0, tzinfo=pytz.utc), tzinfo=pytz.utc)
    return out_datetime

def datetime_to_isostr(dt_obj: Union[datetime.datetime, datetime.date]) -> str:
    return dt_obj.strftime('%Y-%m-%dT%H:%M:%SZ')

def datestr_to_datetime(datestr: str):
    return datetime.datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%SZ").astimezone(pytz.utc)

def check_datestr(input_: Union[str, datetime.datetime]) -> datetime.datetime:
    if type(input_) is datetime.datetime:
        return input_
    else:
        return datestr_to_datetime(input_)
    

def timedelta_to_str(span_: datetime.timedelta):
    out_ms = span_.microseconds // 1000
    return str(out_ms)

class _ObjectID(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return ObjectId(str(v))
        except InvalidId:
            raise ValueError("Not a valid ObjectId")


DType=TypeVar('DType')

class _ndarray(np.ndarray, Generic[DType]):
    """Wrapper class for numpy arrays that stores and validates type information.
    This can be used in place of a numpy array, but when used in a pydantic BaseModel
    or with pydantic.validate_arguments, its dtype will be *coerced* at runtime to the
    declared type.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, val):
        # If numpy cannot create an array with the request dtype, an error will be raised
        # and correctly bubbled up.
        np_array = np.array(val)
        return np_array


def arr_to_lst(arr: np.ndarray):
    return arr.tolist()

BASE_JSON_ENCODERS = {
    datetime.datetime: datetime_to_isostr,
    datetime.date: datetime_to_isostr,
    datetime.timedelta: timedelta_to_str,
    _ObjectID: lambda x: str(x),
    np.ndarray: arr_to_lst
}

#################################
###  [ Pydantic Base Model ]  ###

class Baseline(BaseModel):
    class Config:
        json_encoders = BASE_JSON_ENCODERS


## [ Price Response Models ] ##
class PriceAgg(Baseline):
    vwap_price: float
    volume: int
    tick_datetime: datetime.datetime
    open_price: Optional[float] = None
    close_price: Optional[float] = None

    @validator("tick_datetime", pre=False, always=True)
    def reset_naive_tz(cls, value):
        if value is None:
            return None
        
        dt_val: datetime.datetime = value
        if dt_val.tzinfo is None:
            tz_dt = datetime.datetime.combine(dt_val.date(), dt_val.time(), tzinfo=pytz.utc)
            return tz_dt
        return dt_val.astimezone(pytz.utc)
    
class TickerPricesResponse(Baseline):
    ticker: str
    data: List[PriceAgg]

## [ Ticker Timeline Models ] ##

# e.g. 
#       - GET /stocks/TSLA/timeline?since=7&until=6&period=5m
#       - UptrendsWrapper.get_ticker_timeline_5m(
#           ticker="TSLA", 
#           since_dt=datetime.datetime.now()-datetime.timedelta(days=7), 
#           until_dt=datetime.datetime.now()-datetime.timedelta(days=6)
#         )

class PriceTickInput(Baseline):
    vwap_price: Optional[float] = None
    volume: Optional[int] = None
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    last_valid_close: Optional[float] = None

class SentimentTickInput(Baseline):
    avg_rank: Optional[float] = None
    avg_score: Optional[float] = None
    mentions_count: Optional[int] = None
    mentions_opt: Optional[int] = None
    mentions_pess: Optional[int] = None
    mentions_spec: Optional[int] = None
    mentions_react: Optional[int] = None
    mentions_certainty: Optional[int] = None

class EarningsTickInput(Baseline):
    quarter_num: int
    fiscal_year: int
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[int] = None
    revenue_actual: Optional[int] = None
    event_dt: Optional[datetime.datetime] = None
    event_type: Literal["earnings"]

class FilingTickInput(Baseline):
    filing_type: str
    filing_desc: str
    event_dt: Optional[datetime.datetime] = None
    event_type: Literal["filing"]

class UnifiedTick(Baseline):
    tick_datetime: datetime.datetime
    period_start: datetime.datetime
    period_end: datetime.datetime
    sentiment: SentimentTickInput
    price: PriceTickInput
    events: Optional[List[Union[EarningsTickInput, FilingTickInput]]]

    @validator("period_start", "period_end", "tick_datetime", pre=False, always=True)
    def reset_naive_tz(cls, value):
        if value is None:
            return None
        
        dt_val: datetime.datetime = value
        if dt_val.tzinfo is None:
            tz_dt = datetime.datetime.combine(dt_val.date(), dt_val.time(), tzinfo=pytz.utc)
            return tz_dt
        return dt_val.astimezone(pytz.utc)

class AggPeriod(str, Enum):
    five_minute = "5m"
    hourly = "1h"
    daily = "1d"

class UnifiedTimeline(Baseline):
    ticker: str
    agg_period: AggPeriod
    data: List[UnifiedTick]
    future_events: Optional[List[Union[EarningsTickInput, FilingTickInput]]]


## [ Stock Portfolio Models ] ##

class PortfolioEntry(Baseline): 
    ticker: str
    entry_dt: datetime.datetime
    entry_price: float
    shares: int 
    is_open: Optional[bool] = True
    exit_dt: Optional[datetime.datetime] = None
    exit_price: Optional[float] = None

class AlertKpi(Baseline):
    kpi_name: str
    kpi_value: str
    kpi_direction: str

class TrendingAlert(Baseline): 
    processed_dt: datetime.datetime
    alert_type_name: str
    alert_type_id: str
    ticker: str
    logo_url: str
    company_name: str
    snippet_texts: list[str]
    alert_direction: str
    alert_summary: str
    alert_kpis: Optional[List[AlertKpi]] = []
    is_public: bool
    target_mentions: Optional[int] = None
    anom_score: Optional[float] = None

class TrendingAlertFeedResponse(Baseline):
    alerts: List[TrendingAlert]


class TrendingTopicEntry(Baseline):
    topic_id: str

    # Fields from the DB
    topic_desc: str
    mentions: Optional[int] = 0
    topic_date: datetime.datetime

    # Generated or scored fields
    topic_summary: str
    key_tickers: List[str]
    key_entities: List[str]
    anom_score: float

class TopicsTrendingResp(Baseline):
    trending_topics: List[TrendingTopicEntry]
    since: datetime.datetime
