

from enum import Enum
import datetime
import dateutil
import dateutil.parser
import numpy as np
import pandas as pd
from pydantic import validator
from typing import List, Union, Optional, Dict

from schemas import Baseline


def get_midnight_dt(datelike: Union[datetime.datetime, datetime.date]):
    """Converts the date or datetime to a datetime object with a
    00:00:00 time portion

    returns: datetime of datelike.date(), time set to 0s
    """
    zero_time = datetime.time(hour=0, minute=0, second=0)

    if type(datelike) is datetime.date:
        return datetime.datetime.combine(
            date=datelike,
            time=zero_time
        )
    elif type(datelike) is datetime.datetime:
        return datetime.datetime.combine(
            date=datelike.date(),
            time=zero_time
        )
    raise TypeError(f"Expected date or datetime, got {type(datelike)}")


class AlertDirectionEnum(str, Enum):
    bearish="Bearish"
    bullish="Bullish"
    volatility="Volatility"
    unclear="Unclear"
    mixed="Mixed"

class AlertTimesenseEnum(str, Enum):
    speculative="Speculative"
    reactive="Reactive"
    unsure="Unsure"
    unclear="Unclear"

class AiGeneratedOutlook(Baseline):
    num_sentences: int
    num_disregarded_sentences: Optional[int] = 0
    sentences: List[str]
    summary: str
    raw_outlook: str
    ai_sentiment: Optional[AlertDirectionEnum]
    ai_timesense: Optional[AlertTimesenseEnum]
    
    @validator("ai_sentiment", pre=True)
    def make_sentiment(cls, value: Union[str, AlertDirectionEnum]):
        if type(value) == AlertDirectionEnum:
            return value
        if type(value) == str:
            for enum_obj in AlertDirectionEnum:
                if enum_obj.value.lower() in value.lower():
                    return enum_obj
            return None
        else:
            raise TypeError(f"Expected str or AlertDirectionEnum, got {type(value)}")
        
    @validator("ai_timesense", pre=True)
    def make_timesense(cls, value: Union[str, AlertTimesenseEnum]):
        if type(value) == AlertTimesenseEnum:
            return value
        if type(value) == str:
            for enum_obj in AlertTimesenseEnum:
                if enum_obj.value.lower() in value.lower():
                    return enum_obj
            return None
        else:
            raise TypeError(f"Expected str or AlertTimesenseEnum, got {type(value)}")


class AiQueryLog(Baseline):
    timestamp: datetime.datetime
    prompt: str
    num_prompt_tokens: int
    response: str
    tot_tokens: int
    query_time: float
    input_info: Optional[List[str]] = []
    dedup: Optional[dict] = {}


class AlertConfidenceLevel(str, Enum):
    none="none"
    low="low"
    medium="medium"
    high="high"


class AlertFeatures(str, Enum):
    above_avg_mentions="above avg daily mentions"
    gte_twice_avg_mentions=">= 2x avg daily mentions"
    global_extreme_rank="target_rank > 0.9 or < 0.1"

    pos_spec_ratio=">0 spec ratio"
    anom_spec_ratio=">0.3 spec ratio"
    pos_react_ratio=">0 react ratio"
    anom_react_ratio=">0.3 react ratio"

    high_rank_delta_vs_comp="abs( target_day rank - previous day rank) > 0.1"
    high_rank_delta_vs_ma_comp="abs( target_day rank - previous day's MA rank) > 0.2"
    high_rank_delta_vs_50d_ma="abs( target_day rank - 50d rank MA) > 0.4"
    rank_opp_vs_comps="target_day rank opposite sign vs comparisons"

    high_rank_delta_vs_wavg = "abs( target_day rank - rank_weighed_avg ) >= 0.3"
    rank_extreme_vs_baseline = "target_rank >80th percentile or <20th percentile of baseline ranks"
    rank_outside_baseline = "target_day rank >max or <min rank in baseline"

    target_day_polar_sentiment="target_day has (opt+pess) / target_mentions > 0.8"


class AlertBase(Baseline):
    # DB fields
    str_identifier: str
    entity_type: str

    # Fields required by any alert
    alert_name: str
    alert_type: str
    alert_day: datetime.datetime
    day_window: int
    populated_days_percentage: float
    alert_reason: Optional[str] = None
    alert_summary: Optional[str] = None
    ai_outlook_raw: Optional[str] = None
    ai_sentiment: Optional[AlertDirectionEnum] = None
    ai_timesense: Optional[AlertTimesenseEnum] = None
    alert_direction: Optional[int] = None
    confidence_lvl: Optional[AlertConfidenceLevel] = None
    outlook_obj: Optional[AiGeneratedOutlook] = None
    direction_str: Optional[str] = "N/a"

    # Metadata for our side
    processing_time: Optional[datetime.datetime] = datetime.datetime.now()

    @validator("alert_day", pre=True)
    def parse_alertday(cls, value):
        if isinstance(value, str):
            try:
                return datetime.datetime.strptime(
                    value,
                    "%Y-%m-%d"
                )
            except ValueError:
                return dateutil.parser.isoparse(value)
        if isinstance(value, datetime.datetime):
            # supposed to be the date, set to 00:00:00
            return datetime.datetime.combine(
                date=value.date(),
                time=datetime.time(hour=0, minute=0, second=0)
            )
        if isinstance(value, datetime.date):
            return datetime.datetime.combine(
                date=value,
                time=datetime.time(hour=0, minute=0, second=0)
            )
        else:
            print(f"ERR: Wanted type(date) one of str, date, datetime, got type({str(value)})={str(type(value))}")
            return value
    
    @validator("processing_time", pre=True)
    def parse_proctime(cls, value):
        if type(value) is str:
            return dateutil.parser.isoparse(value)
        if type(value) is datetime.datetime:
            return value
        if type(value) is datetime.date:
            return get_midnight_dt(value)
        else:
            raise TypeError(f"processing_time validator expected str, date, or datetime... got {type(value)}")


class TimelineDayMetaBase(Baseline):
    ticker_date: datetime.datetime
    mentions_count: int
    ticker_rank: float
    mentions_count: int
    mentions_opt: int
    mentions_pess: int
    mentions_spec: int
    mentions_react: int
    mentions_certainty: int

    @validator("ticker_date", pre=True)
    def parse_alertmetadata_day(cls, value):
        if type(value) == str:
            return dateutil.parser.isoparse(value)
        if type(value) == datetime.datetime:
            return datetime.datetime.combine(
                date=value.date(),
                time=datetime.time(hour=0, minute=0, second=0)
            )
        if type(value) == datetime.date:
            return datetime.datetime.combine(
                date=value,
                time=datetime.time(hour=0, minute=0, second=0)
            )
        if type(value) == pd.Timestamp:
            py_dt = value.to_pydatetime()
            return datetime.datetime.combine(
                date=py_dt.date(),
                time=datetime.time(hour=0, minute=0, second=0)
            )
        else:
            print(f"ERR: Wanted type(date) one of str, date, datetime, got type({str(value)})={str(type(value))}")
            return value


class AlertVolumeEnum(str, Enum):
    low="low"
    medium="medium"
    high="high"

############################################################
### High Mention Volume Alert Model + Constituent Models ###
class HVMMentionsMetadata(Baseline):
    one_day_window: int
    two_day_window: int


class AlertMentionsDayMetadata(Baseline):
    date: datetime.datetime
    mentions: int

    @validator("date", pre=True)
    def parse_alertmetadata_day_v1(cls, value):
        if isinstance(value, str):
            return dateutil.parser.isoparse(value)
        if isinstance(value, datetime.datetime):
            return datetime.datetime.combine(
                date=value,
                time=datetime.time(hour=0, minute=0, second=0)
            )
        if isinstance(value, datetime.date):
            return datetime.datetime.combine(
                date=value,
                time=datetime.time(hour=0, minute=0, second=0)
            )
        else:
            print(f"ERR: Wanted type(date) one of str, date, datetime, got type({str(value)})={str(type(value))}")
            return value

class HVMBaselineMetadata(Baseline):
    one_day_avg: float
    one_day_stddev: float
    two_day_avg: float
    two_day_stddev: float

class HVMObservedMetadata(Baseline):
    one_day_stddev_deviation: float
    two_day_stddev_deviation: float

class HighVolumeMentionsAlert(AlertBase):
    ticker: str
    mentions_count: HVMMentionsMetadata
    timeline: List[AlertMentionsDayMetadata]
    baseline: HVMBaselineMetadata
    observed_metrics: HVMObservedMetadata
    alert_name: Optional[str] = "HighMentionVolume"
    alert_type: Optional[str] = "Conversation"
    alert_type_idstr: Optional[str] = "6494bb5b7ea97b45ebfa3f49"
    alert_formatted_name: Optional[str] = "Mentions Spike"
    direction_str: Optional[AlertDirectionEnum] = AlertDirectionEnum.volatility
    alert_features: Optional[List[AlertFeatures]] = []


############################################################
##### Sentiment Spike Alert Model + Constituent Models #####
class RankDayMetadata(TimelineDayMetaBase):
    ma_rank: Optional[float] = None

class SentimentBaselineMetrics(Baseline):
    avg_daily_mentions: float
    avg_rank: float
    weighted_avg_rank: float
    rank_stdev: float
    rank_prev_day: Optional[float] = None
    ma_rank_prev_day: Optional[float] = None
    ma_rank_50d: Optional[float] = None

    @validator("rank_prev_day", "ma_rank_prev_day", "ma_rank_50d")
    def check_float_and_numpy(cls, value):
        if type(value) == np.float64:
            if np.isnan(value):
                return None
            return float(value)
        if value is None:
            return None
        if type(value) is float:
            return value
        else:
            raise TypeError(f"Expected np.float64 or float, got {type(value)}")


class SentimentObservedMetadata(Baseline):
    target_mentions: float
    rank: float
    spec_percent: float
    ma_rank: Optional[float] = None
    target_polarity_score: Optional[float] = None

    
class SentimentSpikeAlert(AlertBase):
    ticker: str
    timeline: List[RankDayMetadata]
    ma_window: int
    volume: AlertVolumeEnum
    baseline: SentimentBaselineMetrics
    observed: SentimentObservedMetadata
    alert_type_idstr: Optional[str] = "6494bb5b7ea97b45ebfa3f4a"
    alert_formatted_name: Optional[str] = "Sentiment Spike"
    direction_str: AlertDirectionEnum
    alert_features: Optional[List[AlertFeatures]] = []


SENTIMENT_SPIKE_FEATURES = [
    AlertFeatures.gte_twice_avg_mentions, 
    AlertFeatures.global_extreme_rank,
    AlertFeatures.anom_react_ratio, 
    AlertFeatures.anom_spec_ratio,
    AlertFeatures.rank_opp_vs_comps, 
    AlertFeatures.high_rank_delta_vs_ma_comp,
    AlertFeatures.high_rank_delta_vs_50d_ma, 
    AlertFeatures.high_rank_delta_vs_wavg,
    AlertFeatures.rank_extreme_vs_baseline, 
    AlertFeatures.target_day_polar_sentiment
]


def flatten_sentiment_spikes(alert_lst_raw: List[SentimentSpikeAlert]) -> Union[None, pd.DataFrame]:
    alert_lst = [x for x in alert_lst_raw if type(x)==SentimentSpikeAlert]
    
    if len(alert_lst)==0:
        print(f"[ERR][flatten_sentiment_spikes] got no SentimentSpikeAlerts (input list had length={len(alert_lst_raw)})")
        return None
    
    # Will turn nested stuff we want into flat list for CSV's
    flattened_lst = []
    for alert_obj in alert_lst:
        alert_d = alert_obj.model_dump(exclude={"timeline"})
        
        features_lst: List[AlertFeatures] = alert_d.pop("alert_features")
        for feature in SENTIMENT_SPIKE_FEATURES:
            if feature in features_lst:
                alert_d["feature."+str(feature.name)] = 1
            else:
                alert_d["feature."+str(feature.name)] = 0
        
        baseline_d: dict = alert_d.pop("baseline")
        for baseline_k in baseline_d.keys():
            alert_d[f"baseline.{baseline_k}"] = baseline_d[baseline_k]
        
        observed_d: dict = alert_d.pop("observed")
        for observed_k in observed_d.keys():
            alert_d[f"observed.{observed_k}"] = observed_d[observed_k]
        flattened_lst.append(alert_d)
    
    out_df = pd.DataFrame(data=flattened_lst)
    print(f"[INFO][flatten_sentiment_spikes] got {out_df.shape[0]} alerts, returning df")
    return out_df

