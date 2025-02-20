import mysql.connector
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime, timedelta
import re
import pandas_market_calendars as mcal

# Connect to MySQL database
mydb = mysql.connector.connect(
  host="alvcantu.mysql.pythonanywhere-services.com",
  user="alvcantu",
  password="h63Efp09-d",
  database="alvcantu$default"
)

cursor = mydb.cursor()

# Function to perform quality checks
def quality_checks(df):
    issues = []
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'

    # Checks if data is in yyyy-mm-dd format
    if not df['date'].apply(lambda x: bool(re.match(date_pattern, str(x)))).all():
        issues.append("'date' column is not in 'YYYY-MM-DD' format")

    # Ticker has to be string
    if not df['ticker'].dtype == 'object':
        issues.append("'ticker' column is not string type")

    # Forecast price ARIMA has to be float type
    if not pd.api.types.is_float_dtype(df['forecast_price_arima']):
        issues.append("'forecast_price_arima' column is not float type")

    # Check for empty values, excluding close_price
    for column in df.columns:
        if column != 'close_price' and df[column].isnull().sum() > 0:
            issues.append(f"Empty values found in '{column}' column")

    # Check if there are duplicate date+ticker combinations
    if df.duplicated(subset=['date', 'ticker']).sum() > 0:
        issues.append("Duplicate entries found for date+ticker combination")

    # Check if any date is more than 10 days in the future
    today = datetime.now().date()
    future_threshold = today + timedelta(days=10)
    future_dates = df[pd.to_datetime(df['date']).dt.date > future_threshold]
    if not future_dates.empty:
        issues.append("Dates more than 10 days into the future found")

    return issues

# Get the NYSE calendar
nyse = mcal.get_calendar('NYSE')
# Get the Saudi Stock Exchange calendar, exception for Saudi Aramco used later
saudi = mcal.get_calendar('XSAU')
# Get the Saudi Stock Exchange calendar, exception for Petrochina used later
hongkong = mcal.get_calendar('HKEX')

# Extract only the most recent 30 trading days of data
query = """
SELECT date, ticker, close_price
FROM ST_FactPrices
WHERE date <= CURDATE()
ORDER BY date DESC;
"""
cursor.execute(query)
data = cursor.fetchall()

# Convert to DataFrame
df = pd.DataFrame(data, columns=['date', 'ticker', 'close_price'])
df['date'] = pd.to_datetime(df['date'])

# Perform forecasting for each ticker
forecast_results = []
unique_tickers = df['ticker'].unique()

for ticker in unique_tickers:
    ticker_data = df[df['ticker'] == ticker].set_index('date')['close_price']

    # Set the frequency to business day
    if ticker == '2222.SR':
        calendar = saudi
        ticker_data = ticker_data.asfreq(pd.tseries.offsets.CustomBusinessDay(calendar=saudi))
    if ticker == '0857.HK':
        calendar = hongkong
        ticker_data = ticker_data.asfreq(pd.tseries.offsets.CustomBusinessDay(calendar=hongkong))
    else:
        calendar = nyse
        ticker_data = ticker_data.asfreq('B')

    # Get the next 5 trading days for this ticker
    last_date = ticker_data.index.max()
    next_trading_days = calendar.valid_days(start_date=last_date + timedelta(days=1), end_date=last_date + timedelta(days=20))[:5]

    # Fit ARIMA model
    model = ARIMA(ticker_data, order=(1,1,1))
    model_fit = model.fit()

    # Forecast next 5 trading days
    forecast = model_fit.forecast(steps=5)

    for date, price in zip(next_trading_days, forecast):
        forecast_results.append({
            'ticker': ticker,
            'date': date.strftime('%Y-%m-%d'),
            'forecast_price_arima': price
        })

# Convert forecast results to DataFrame
forecast_df = pd.DataFrame(forecast_results)
# Perform quality checks
# forecast_df['close_price'] = np.nan  # Add this column to pass quality checks
issues = quality_checks(forecast_df)

if issues:
    print("Quality check issues found:")
    for issue in issues:
        print(f"- {issue}")
else:
    print("All quality checks passed. Updating forecasts in ST_FactPrices.")

    # Update forecasts in ST_FactPrices, note the same ON DUPLICATE KEY UPDATE clause to only insert forecast_prices
    update_query = """
    INSERT INTO ST_FactPrices (ticker, date, close_price, forecast_price_arima)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    forecast_price_arima = VALUES(forecast_price_arima)
    """

    values = [(row['ticker'], row['date'], None, row['forecast_price_arima'])
              for _, row in forecast_df.iterrows()]

    cursor.executemany(update_query, values)
    mydb.commit()

    print(f"{len(values)} forecast records updated in ST_FactPrices.")


# Execute query to delete rows with no close prices before today
delete_query = """
DELETE FROM ST_FactPrices
WHERE close_price IS NULL
AND date < CURDATE()
"""
cursor.execute(delete_query)
mydb.commit()

# Close the cursor and database connection
cursor.close()
mydb.close()