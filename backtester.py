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
from data import UptrendsWrapper
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import numpy as np

api = UptrendsWrapper()

def calculate_slope(y):
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    return slope

class Stock:
    def __init__(self, tickername):
        self.ticker = tickername
        timelineRes = api.get_ticker_timeline_daily(ticker=tickername, since_dt=datetime.datetime.now() - datetime.timedelta(days=180), until_dt=datetime.datetime.now())
        df = pd.DataFrame(columns=['price', 'rank'])
        prices = []
        ranks = []
        for data in timelineRes.data:
            prices.append(data.price.close_price)
            ranks.append(data.sentiment.avg_rank)
        df['price'] = prices
        df['rank'] = ranks
        df = df.dropna()
        df = df.reset_index(drop=True)
        self.df = df
        self.prices = df['price']
        self.ranks = df['rank']

    def get_dataframe(self):
        return self.df

    def get_prices(self):
        return self.prices

    def get_ranks(self):
        return self.ranks


class MACDStrategy:
    def __init__(self, stock):
        self.rank_ma9 = stock.ranks.rolling(9).mean()
        self.rank_ma21 = stock.ranks.rolling(21).mean()
        self.rank_ma9_prev = self.rank_ma9.shift()
        self.rank_ma21_prev = self.rank_ma21.shift()

    def get_rank_ma9(self):
        return self.rank_ma9

    def get_rank_ma21(self):
        return self.rank_ma21
    
    def get_rank_ma9_prev(self):
        return self.rank_ma9_prev

    def get_rank_ma21_prev(self):
        return self.rank_ma21_prev
    

class SlopeStrategy:
    def __init__(self, stock):
        self.firstDeri = stock.ranks.rolling(window=5).apply(calculate_slope)
        self.secondDeri = self.firstDeri.rolling(window=5).apply(calculate_slope)
        self.firstDeri_prev = self.firstDeri.shift()
        self.secondDeri_prev = self.secondDeri.shift()

    def get_first_deri(self):
        return self.firstDeri
    
    def get_second_deri(self):
        return self.secondDeri
    
    def get_first_deri_prev(self):
        return self.firstDeri_prev
    
    def get_second_deri_prev(self):
        return self.secondDeri_prev

class Trade:
    def __init__(self, stock):
        self.ticker = stock.ticker
        self.position = 'none'
        self.win = 0
        self.total = 0
        self.enterTimes = []
        self.enterPrices = []

    def enterBullishTrade(self, stock, index):
        self.enterPrice = stock.prices[index]
        self.target = self.enterPrice * 1.03
        self.stopLoss = self.enterPrice * 0.97
        self.sentiment = 'Bullish'
        self.position = "entered"
        self.enterTimes.append([index, self.sentiment])
        self.enterPrices.append(self.enterPrice)

    def enterBearishTrade(self, stock, index):
        self.enterPrice = stock.prices[index]
        self.target = self.enterPrice * 0.98
        self.stopLoss = self.enterPrice * 1.02
        self.sentiment = 'Bearish'
        self.position = "entered"
        self.enterTimes.append([index, self.sentiment])
        self.enterPrices.append(self.enterPrice)

    def exitWin(self):
        self.win += 1
        self.total += 1
        self.position = 'none'
    
    def exitLoss(self):
        self.total += 1
        self.position = 'none'

def plot(df, enterTimes, enterPrices):
    # Create a figure and a subplot
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    # Plotting the stock price on the first y-axis
    color = 'tab:blue'
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Price', color=color)
    ax1.plot(df.index, df['price'], label='Stock Price', color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    # Plotting the entry points with different colors based on sentiment
    for i, (index, sentiment) in enumerate(enterTimes):
        entry_color = 'green' if sentiment == 'Bullish' else 'red'
        ax1.scatter(index, enterPrices[i], color=entry_color, label=f'{sentiment} Entry' if i == 0 else "", marker='o')

    # Create a second y-axis for the rank
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Rank', color=color)  # we already handled the x-label with ax1
    ax2.plot(df.index, df['rank'], label='Rank', color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Adding a legend for the first axis
    ax1.legend(loc='upper left')
    
    # Optionally, you can add a legend for ax2 as well, but you need to handle it separately
    # ax2.legend(loc='upper right')

    fig.tight_layout()  # To ensure there's no layout overlap
    plt.title('Stock Price with Entry Points and Rank')
    plt.show()


totalWin = 0
totalTotal = 0
tickers = ['TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'JPM', 'CAT', 'PFE', 'COIN', 'NVDA', 'AMD', 'MARA', 'AAPL', 'JPM', 'CRM']

for company in tickers:
    # Initialize stock, strategy, trade classes
    stock = Stock(company)
    print(stock.ticker)
    strategy = MACDStrategy(stock)
    trade = Trade(stock)
    ccf = sm.tsa.stattools.ccf(strategy.get_rank_ma21()[21:].to_numpy(), stock.df['price'][21:].to_numpy(), adjusted=False)
    max_corr_lag = np.argmax(np.abs(ccf))
    max_corr = ccf[max_corr_lag]
    if max_corr >= 0.5 and max_corr_lag > 0:
        for index in stock.prices.index:
            # Get the current data
            price = stock.prices[index]
            rank = stock.ranks[index]
            # firstDeri = strategy.get_first_deri()[index]
            # secondDeri = strategy.get_second_deri()[index]
            # firstDeri_prev = strategy.get_first_deri_prev()[index]
            # secondDeri_prev = strategy.get_second_deri_prev()[index]
            slow = strategy.get_rank_ma21()[index]
            fast = strategy.get_rank_ma9()[index]
            slow_prev = strategy.get_rank_ma21_prev()[index]
            fast_prev = strategy.get_rank_ma9_prev()[index]

            # Enter a trade
            if trade.position == 'none':
                # if firstDeri > 0 and firstDeri_prev < 0:
                #     if secondDeri > 0:
                #         trade.enterBullishTrade(stock, index)
                # elif firstDeri < 0 and firstDeri_prev > 0:
                #     trade.enterBearishTrade(stock, index)
                if fast > slow and fast_prev < slow_prev:
                    trade.enterBullishTrade(stock, index)
                elif slow > fast and slow_prev < fast_prev:
                    trade.enterBearishTrade(stock, index)
            # Exit the trade
            elif trade.position == 'entered':
                if trade.sentiment == 'Bullish':
                    if trade.target < price:
                        trade.exitWin()
                    elif trade.stopLoss > price:
                        trade.exitLoss()
                elif trade.sentiment == 'Bearish':
                    if trade.target > price:
                        trade.exitWin()
                    elif trade.stopLoss < price:
                        trade.exitLoss()
        try:
            winrate = (trade.win/trade.total) * 100
        except:
            winrate = 'NA'
        print(f'{company}: {trade.win}/{trade.total} - {winrate}')



# plot(stock.df, trade.enterTimes, trade.enterPrices)
        

# stock = Stock("MARA")
# strategy = MACDStrategy(stock)
# # plot(stock.df, [], [])

# # Calculate the correlation coefficient
# correlation = stock.df['price'][21:].corr(strategy.get_rank_ma21()[21:])
# print(f'Correlation coefficient: {correlation}')




# # Sample data
# rank = strategy.get_rank_ma21()[21:].to_numpy()
# price = stock.df['price'][21:].to_numpy()

# # Compute cross-correlation
# ccf = sm.tsa.stattools.ccf(rank, price, adjusted=False)

# # Identify the lag with the highest correlation
# max_corr_lag = np.argmax(np.abs(ccf))
# max_corr = ccf[max_corr_lag]

# print(f'Best lag: {max_corr_lag}, Maximum correlation: {max_corr}')