import yfinance as yf
import mysql.connector
import pandas as pd
import re

# Connect to MySQL database
mydb = mysql.connector.connect(
  host="alvcantu.mysql.pythonanywhere-services.com",
  user="alvcantu",
  password="h63Efp09-d",
  database="alvcantu$default"
)
cursor = mydb.cursor()

# SQL queries to extract distinct tickers
query_fact = "SELECT DISTINCT ticker FROM ST_FactPrices"
query_dim = "SELECT DISTINCT ticker FROM ST_DimCompany"

# Execute query to get tickers from ST_DimCompany
cursor.execute(query_dim)
dim_tickers = set(ticker[0] for ticker in cursor.fetchall())

# Execute query to get tickers from ST_FactPrices
cursor.execute(query_fact)
fact_tickers = set(ticker[0] for ticker in cursor.fetchall())

# Separate tickers into two lists
new_tickers = list(dim_tickers - fact_tickers)
existing_tickers = list(dim_tickers.intersection(fact_tickers))

# Set data variable
data = {}

# Extract all data for brand new tickers
if new_tickers:
    new_data = yf.download(" ".join(new_tickers), period="max")
    data.update(new_data)

# Extract only 1 month of data for existing tickers to save on compute power
if existing_tickers:
    existing_data = yf.download(" ".join(existing_tickers), period="1mo")
    data.update(existing_data)

# Function to download and format data
def download_and_format_data(tickers, period="max"):
    if tickers:
        # Download data
        data = yf.download(" ".join(tickers), period=period)
        
        # Ensure data is a DataFrame even if there's only one ticker
        if not isinstance(data.columns, pd.MultiIndex):
            # Convert single ticker data to MultiIndex format
            data.columns = pd.MultiIndex.from_product([data.columns, [tickers[0]]])
        
        # Melt the DataFrame to get it into the date, ticker, close_price format
        df = data['Close'].stack().reset_index()
        df.columns = ['Date', 'Ticker', 'Close_Price']
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        return df.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    return pd.DataFrame()  # Return an empty DataFrame if no tickers

# Download data for new tickers
new_data_df = download_and_format_data(new_tickers)

# Download only 1 month of data for existing tickers
existing_data_df = download_and_format_data(existing_tickers, period="1mo")

# Combine both dataframes
df_combined = pd.concat([new_data_df, existing_data_df], ignore_index=True)

# Ensure all column names are lowercase
df_combined.columns = df_combined.columns.str.lower()

# Remove rows where Close_Price is NaN
df_combined = df_combined.dropna(subset=['close_price'])

# Data quality checks
def quality_checks(df):
    issues = []
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not df['date'].apply(lambda x: bool(re.match(date_pattern, str(x)))).all():
        issues.append("'date' column is not in 'YYYY-MM-DD' format")
    if not df['ticker'].dtype == 'object':
        issues.append("'ticker' column is not string type")
    if not pd.api.types.is_float_dtype(df['close_price']):
        issues.append("'close_price' column is not float type")
    for column in df.columns:
        if df[column].isnull().sum() > 0:
            issues.append(f"Empty values found in '{column}' column")
    if df.duplicated(subset=['date', 'ticker']).sum() > 0:
        issues.append("Duplicate entries found for date+ticker combination")
    return issues

# Perform quality checks
issues = quality_checks(df_combined)

# Output issues if exists
if issues:
    print("Quality check issues found:")
    for issue in issues:
        print(f"- {issue}")
else:
    print("All quality checks passed.")

    # Prepare the SQL query for inserting or updating
    # Note the ON DUPLICATE KEY clause which only updates the close_price if it exists already, and most likely does from forecasting (see next script)
    upsert_query = """
    INSERT INTO ST_FactPrices (ticker, date, close_price)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
    close_price = VALUES(close_price)
    """

    # Convert DataFrame to list of tuples
    values = list(df_combined[['ticker', 'date', 'close_price']].itertuples(index=False, name=None))

    # Execute the query
    cursor.executemany(upsert_query, values)

    # Commit the changes
    mydb.commit()

    print(f"{len(values)} records inserted or updated in ST_FactPrices.")

# Close the cursor and database connection
cursor.close()
mydb.close()