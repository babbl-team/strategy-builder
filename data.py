import datetime
from dotenv import load_dotenv
import json
import os
import requests
from typing import List, Optional
import json
import prices
import datetime
import pandas as pd

# Loads 'env.shared' data into os.environ
load_dotenv(".env.shared")

from alert_types import SentimentSpikeAlert
from schemas import UnifiedTimeline, AggPeriod


class UptrendsWrapper:
    def __init__(self, verbose:bool = False):
        self.verbose = verbose
        self.api_key = os.environ.get("BASIC_UPTRENDS_API_KEY")
        self.dev_api_base = os.environ.get("DEV_UPTRENDS_BASE_API")
        self.prod_api_base = os.environ.get("PROD_UPTRENDS_BASE_API")

        self.api_base = self.dev_api_base
        
        # Let's grab a session ID
        sess_resp = requests.get(self.api_base+f"/sessions/?user_key={self.api_key}")
        if sess_resp.status_code != 200:
            #print(f"[ERROR][UW.__init__] Got status code {sess_resp.status_code} from API ({self.api_base})")
            #print(sess_resp.text)
            self.session_id = "sess-placeholder"
        else:
            sess_d = sess_resp.json()
            self.session_id = sess_d["session_id"]
            if self.verbose:
                print(f"[INFO][UW.__init__] Got session ID {self.session_id}")
        
    def get_alert_objs(self, since_days_ago: int=7, until_days_ago: int=0, max_results:int=200, ticker: Optional[str]=None):
        arg_str = f"since={since_days_ago}&until={until_days_ago}&max_results={max_results}"
        if ticker is not None:
            ticker = ticker.upper()
            # add in the ticker arg
            arg_str += f"&ticker={ticker}"

        alert_resp = requests.get(f"{self.api_base}/events/feed/alerts?{arg_str}")
        # print(alert_resp.status_code)
        alert_d = alert_resp.json()
        alerts_lst: List[dict] = alert_d["data"]

        alerts_objs = [SentimentSpikeAlert.model_validate(x) for x in alerts_lst]
        
        if self.verbose:
            print(f"[INFO][UW.get_alert_objs] Got {len(alerts_objs)} alerts, ticker set to '{ticker}'")
        return alerts_objs
    
    def _get_ticker_timeline_generic(
            self,
            ticker: str,
            since_dt: datetime.datetime,
            until_dt: datetime.datetime,
            period: AggPeriod
    ) -> UnifiedTimeline:
        """> Returns a UnifiedTimeline object for a given ticker, between these datetimes. 
        NOTE: Each datapoint in UnifiedTimeline.data is an aggregation chosen by the 'period' arg
            containing the sentiment data, price data, and events data that happened in each window
        """
        ticker = ticker.upper()
        since_dt = since_dt.astimezone(datetime.timezone.utc)
        until_dt = until_dt.astimezone(datetime.timezone.utc)

        since_dt_str = since_dt.isoformat().replace("+00:00", "Z")
        until_dt_str = until_dt.isoformat().replace("+00:00", "Z")

        timeline_resp = requests.get(
            f"{self.api_base}/stocks/{ticker}/timeline?since={since_dt_str}&until={until_dt_str}&period={period.value}"
        )
        if timeline_resp.status_code != 200:
            print(f"[ERROR][UW.get_ticker_timeline_5m] Got status code {timeline_resp.status_code} from API ({self.api_base})")
            print(timeline_resp.text)
            return None
        
        raw_data = timeline_resp.json()
        timeline_obj = UnifiedTimeline.model_validate(raw_data)
        return timeline_obj
        
    def get_ticker_timeline_5m(
            self, 
            ticker: str, 
            since_dt: datetime.datetime, 
            until_dt: datetime.datetime
        ) -> UnifiedTimeline:
        """> Returns a UnifiedTimeline object for a given ticker, between these datetimes. 
        NOTE: Each datapoint in UnifiedTimeline.data is a 5-minute aggregation 
            containing the sentiment data, price data, and events data that happened in that 5-minute window
        """
        timeline_obj = self._get_ticker_timeline_generic(ticker, since_dt, until_dt, AggPeriod.five_minute)
        return timeline_obj
    
    def get_ticker_timeline_hourly(
            self, 
            ticker: str, 
            since_dt: datetime.datetime, 
            until_dt: datetime.datetime
        ) -> UnifiedTimeline:
        """> Returns a UnifiedTimeline object for a given ticker, between these datetimes. 
        NOTE: Each datapoint in UnifiedTimeline.data is an hourly aggregation 
            containing the sentiment data, price data, and events data that happened in that 1-hour window
        """
        timeline_obj = self._get_ticker_timeline_generic(ticker, since_dt, until_dt, AggPeriod.hourly)
        return timeline_obj
    
    def get_ticker_timeline_daily(
            self, 
            ticker: str, 
            since_dt: datetime.datetime, 
            until_dt: datetime.datetime
        ) -> UnifiedTimeline:
        """> Returns a UnifiedTimeline object for a given ticker, between these datetimes. 
        NOTE: Each datapoint in UnifiedTimeline.data is a daily aggregation 
            containing the sentiment data, price data, and events data that happened in that day's window
        """
        timeline_obj = self._get_ticker_timeline_generic(ticker, since_dt, until_dt, AggPeriod.daily)
        return timeline_obj


if __name__=="__main__":
    api = UptrendsWrapper(verbose=True)
    alerts = api.get_alert_objs(since_days_ago=7, until_days_ago=0)
    timelineRes = api.get_ticker_timeline_hourly(ticker='TSLA', since_dt=datetime.datetime.now() - datetime.timedelta(days=7), until_dt=datetime.datetime.now())
    print(len(timelineRes.data))


    # tsla_alerts = api.get_alert_objs(
    #     since_days_ago=180,
    #     until_days_ago=0,
    #     ticker=ticker
    # )


    # moving_avg_df = pd.DataFrame(columns=['date', 'rank', '9day_avg', '21day_avg', 'price'])

    # ranks = []
    # date = []

    # for alert in tsla_alerts:
    #     ranks.append(json.loads(alert.model_dump_json(indent=2))['observed']['rank'])
    #     date.append(json.loads(alert.model_dump_json(indent=2))['alert_day'][0:10])
    # ranks.reverse()
    # date.reverse()
    # moving_avg_df['rank'] = ranks
    # moving_avg_df['date'] = date
    # moving_avg_df['9day_avg'] = moving_avg_df['rank'].rolling(window=9).mean()
    # moving_avg_df['21day_avg'] = moving_avg_df['rank'].rolling(window=21).mean()
    #  # 180 rows



    # # direction_str
    # # alert_day
    # output = []
    # for alert in tsla_alerts:
    #     day = json.loads(alert.model_dump_json(indent=2, exclude={'timeline'}))['alert_day']
    #     direction = json.loads(alert.model_dump_json(indent=2, exclude={'timeline'}))['direction_str']
    #     output.append([day[0:10], direction])


    # tsla_prices = prices.get_ticker_daily_prices(
    #         ticker,
    #         start_dt= datetime.datetime.now()-datetime.timedelta(days=180),
    #         end_dt=datetime.datetime.now()
    #     )



    # for i in range(len(tsla_prices)):
    #     cur_day = str(tsla_prices[i].tick_datetime)[0:10]
    #     price = tsla_prices[i].close_price
    #     if cur_day in moving_avg_df['date'].values:
    #         row_index = moving_avg_df[moving_avg_df['date'] == cur_day].index[0]
    #         moving_avg_df.at[row_index, 'price'] = price

    # print(moving_avg_df)



    # pos = "none"
    # win = 0
    # total = 0
    # totalWin = 0
    # totalTotal = 0
    # enterPrice = None
    # enterTime = None
    # threshold = 0.05
    # for i in moving_avg_df.index[21:]:
    #     cur_price = moving_avg_df['price'][i]
    #     ma9 = moving_avg_df['9day_avg'][i]
    #     ma21 = moving_avg_df['21day_avg'][i]
    #     ma9_prev = moving_avg_df['9day_avg'][i-1]
    #     ma21_prev = moving_avg_df['21day_avg'][i-1]
    #     if pos == 'none':
    #         if ma9 > ma21 and ma9_prev <= ma21_prev:
    #             pos = 'entered'
    #             enterPrice = price
    #             cur_sentiment = 'Bullish'
    #         if ma9 < ma21 and ma9_prev >= ma21_prev:
    #             pos = 'entered'
    #             enterPrice = price
    #             cur_sentiment = 'Bearish' 
    #     elif pos == 'entered':
    #         if cur_sentiment == "Bullish":
    #             if cur_price > enterPrice * (1 + threshold): # Bullish Win
    #                 win += 1
    #                 total += 1
    #                 pos = "none"
    #                 totalWin += 1
    #                 totalTotal += 1
    #             elif cur_price < enterPrice * (1 - threshold): # Bullish Loss
    #                 total += 1
    #                 pos = "none"
    #                 totalTotal += 1
    #         else: # Bearish setup: 1% threshold up or down
    #             if cur_price < enterPrice * (1 - threshold): # Bearish Win
    #                 win += 1
    #                 total += 1
    #                 pos = "none"
    #                 totalWin += 1
    #                 totalTotal += 1
    #             elif cur_price > enterPrice * (1 + threshold): # Bearish Loss
    #                 total += 1
    #                 pos = "none"
    #                 totalTotal += 1

    # try:
    #     winrate = (win/total) * 100
    #     print(f'Success Rate: {winrate}%')
    # except ZeroDivisionError:
    #     print(f'Success Rate: 0%')
    # print(f'{win}/{total}')


    # import matplotlib.pyplot as plt

    # # Assuming moving_avg_df is your DataFrame
    # # Replace 'date', 'price', '9_day_avg', and '21_day_avg' with your actual column names
    # fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]}, sharex=True)

    # # Plot the price at the top
    # ax1.plot(moving_avg_df['date'], moving_avg_df['price'], label='Price', marker='o', color='blue')
    # ax1.set_ylabel('Price')
    # ax1.legend()

    # # Plot the moving averages at the bottom
    # ax2.plot(moving_avg_df['date'], moving_avg_df['9day_avg'], label='9-Day MA', marker='o', color='green')
    # ax2.plot(moving_avg_df['date'], moving_avg_df['21day_avg'], label='21-Day MA', marker='o', color='orange')
    # ax2.set_xlabel('Date')
    # ax2.set_ylabel('Moving Averages')
    # ax2.legend()

    # plt.suptitle('Price and Moving Averages Over Time')
    # plt.show()


    # pos = "none"
    # win = 0
    # total = 0
    # totalWin = 0
    # totalTotal = 0
    # enterPrice = None
    # enterTime = None
    # threshold = 0.05
    # for i in range(len(tsla_prices)):
    #     open_price = tsla_prices[i].open_price
    #     close_price = tsla_prices[i].close_price
    #     cur_day = str(tsla_prices[i].tick_datetime)[0:10]
    #     while len(output) > 0:
    #         if int(output[-1][0].split("-")[2]) < int(cur_day.split("-")[2]) or int(output[-1][0].split("-")[1]) < int(cur_day.split("-")[1]): # removing the next output if it's in the past compared to cur_day
    #             output.pop()
    #         else:
    #             break # Removed enough alerts
    #     else:
    #         break # No alerts to act on so break
    #     if pos == "none": # No current position
    #         alert_time = output[-1][0] # Grab the next possible alert
    #         if alert_time == cur_day: # Check if the alert day is equal to the current day
    #             current_alert = output.pop() # Remove from list of alerts
    #             pos = "entered"
    #             cur_sentiment = current_alert[1] # 'Bullish' or 'Bearish'
    #             enterPrice = close_price # Assume entry is the closing price (we don't have intra-day)
    #     elif pos == "entered" and current_alert[0] != cur_day: # Check if we entered a position and the current day is not the same as the alert day
    #         if cur_sentiment == "Bullish": # Bullish setup: 1% threshold up or down
    #             if max(close_price, open_price) > enterPrice * (1 + threshold): # Bullish Win
    #                 win += 1
    #                 total += 1
    #                 pos = "none"
    #                 totalWin += 1
    #                 totalTotal += 1
    #             elif max(close_price, open_price) < enterPrice * (1 - threshold): # Bullish Loss
    #                 total += 1
    #                 pos = "none"
    #                 totalTotal += 1
    #         else: # Bearish setup: 1% threshold up or down
    #             if min(open_price, close_price) < enterPrice * (1 - threshold): # Bearish Win
    #                 win += 1
    #                 total += 1
    #                 pos = "none"
    #                 totalWin += 1
    #                 totalTotal += 1
    #             elif max(close_price, open_price) > enterPrice * (1 + threshold): # Bearish Loss
    #                 total += 1
    #                 pos = "none"
    #                 totalTotal += 1
    # try:
    #     winrate = (win/total) * 100
    #     print(f'Success Rate: {winrate}%')
    # except ZeroDivisionError:
    #     print(f'Success Rate: 0%')
    # print(f'{win}/{total}')