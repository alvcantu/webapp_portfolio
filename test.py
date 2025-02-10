import pandas_market_calendars as mcal
from datetime import timedelta
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA


# Create a calendar for the Saudi Stock Exchange
saudi = mcal.get_calendar('XSAU')
nyse = mcal.get_calendar('NYSE')

ticker = 'MSFT'

# Simulate data from 2025-02-06 to today
start_date = pd.Timestamp('2025-02-05')
end_date = pd.Timestamp('2025-02-06')
date_range = pd.date_range(start=start_date, end=end_date, freq='D')

data = [{'date': date.strftime('%Y-%m-%d'), 'ticker': 'MSFT', 'close_price': 100 + i} for i, date in enumerate(date_range)]

df = pd.DataFrame(data, columns=['date', 'ticker', 'close_price'])
ticker_data = df[df['ticker'] == ticker].set_index('date')['close_price']


if ticker == '2222.SR':
    calendar = saudi
    ticker_data = ticker_data.asfreq(pd.tseries.offsets.CustomBusinessDay(calendar=saudi))
else:
    calendar = nyse
    ticker_data = ticker_data.asfreq(pd.tseries.offsets.CustomBusinessDay(calendar=nyse))

# Get the next 5 trading days for this ticker
last_date = ticker_data.index.max()
next_trading_days = calendar.valid_days(start_date=last_date + timedelta(days=1), end_date=last_date + timedelta(days=20))[:5]

print(next_trading_days)

# Fit ARIMA model
model = ARIMA(ticker_data, order=(1,1,1))
model_fit = model.fit()

# Forecast next 5 trading days
forecast = model_fit.forecast(steps=5)

forecast_results = []

for date, price in zip(next_trading_days, forecast):
    forecast_results.append({
        'ticker': ticker,
        'date': date.strftime('%Y-%m-%d'),
        'forecast_price_arima': price
    })

# Convert forecast results to DataFrame
forecast_df = pd.DataFrame(forecast_results)

print(forecast_df)
