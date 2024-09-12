import pandas as pd
import numpy as np
import datetime
import pandas as pd
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
import xgboost as xgb
import random

# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor(dictionary=True) # Outputs as dictionary
    return mydb, cursor

def execute_query(query):
    mydb, cursor = get_db_connection()
    cursor.execute(query)
    # Fetch all rows as a list of dictionaries where keys are column names
    rows = cursor.fetchall()
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(rows)
    
    # Close the connection
    cursor.close()
    mydb.close()
    
    return df

query = '''
SELECT 
    t.InvoiceID AS InvoiceID,
    i.CustomerID AS CustomerID,
    i.InvoiceDate AS InvoiceDate,
    i.Country AS Country,
    t.StockCode AS StockCode,
    t.Description AS Description,
    t.Quantity AS Quantity,
    t.UnitPrice AS UnitPrice,
    (t.Quantity * t.UnitPrice) AS Sales
FROM 
    ONR_FactTransactions t
JOIN 
    ONR_DimInvoice i ON t.InvoiceID = i.InvoiceID;
'''

df = execute_query(query)

# Convert to valid data types
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')
# Feature Engineering
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['Day'] = df['InvoiceDate'].dt.day
df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')

# Encode categorical variables
le = LabelEncoder()
df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
df['Country'] = le.fit_transform(df['Country'])

# Assuming 'Sales' is our target variable
X = df[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']]
y = df['Sales']

# Features the model was trained on
features = ['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt1_xgboost_mlmodel_online_retail.json')

# Assuming you've already loaded the DataFrame df and done the necessary feature engineering
# Find the last InvoiceDate in your current data
last_date = df['InvoiceDate'].max()

# Create future dates for the next 4 months
num_months = 3
future_dates = pd.date_range(last_date + pd.DateOffset(1), periods=num_months*30, freq='D')

# Get unique valid combinations of CustomerID, StockCode, and Country from the historical data
# Assuming those combinations are good estimators of future sales
valid_combinations = df[['CustomerID', 'StockCode', 'Country']].drop_duplicates()

# Initialize an empty list to hold the future data
future_data = []

# For each future date, randomly sample from the valid combinations and create feature rows
sample_size = 1625  # Using the following SQL query to get the average number of unique combinations per date
'''
WITH UniqueCombinations AS (
    SELECT
        i.InvoiceDate,
        i.CustomerID,
        t.StockCode,
        i.Country
    FROM
        ONR_DimInvoice i
    JOIN
        ONR_FactTransactions t ON i.InvoiceID = t.InvoiceID
    GROUP BY
        i.InvoiceDate,
        i.CustomerID,
        t.StockCode,
        i.Country
),
CountsPerDate AS (
    SELECT
        InvoiceDate,
        COUNT(*) AS combinations_count
    FROM
        UniqueCombinations
    GROUP BY
        InvoiceDate
)
SELECT
    AVG(combinations_count) AS avg_unique_combinations_per_date
FROM
    CountsPerDate LIMIT 6900;
'''

for date in future_dates:
    year = date.year
    month = date.month
    day = date.day
    day_of_week = date.dayofweek
    # Randomly sample valid combinations for this date
    sampled_combinations = valid_combinations.sample(n=sample_size, replace=False)
    
    # Create future data for each sampled combination
    for _, row in sampled_combinations.iterrows():
        customer_id = row['CustomerID']
        stock_code = row['StockCode']
        country = row['Country']
        
        future_data.append({
            'CustomerID': customer_id,
            'StockCode': stock_code,
            'Year': year,
            'Month': month,
            'Day': day,
            'DayOfWeek': day_of_week,
            'Country': country
        })

# Convert the future data into a DataFrame
future_df = pd.DataFrame(future_data)

#Encode categorical variables for the future data
future_df['Season'] = le.transform(future_df['Season'])  # Use the same encoder from the original dataset

# Select the features for the model
X_future = future_df[features]

# Predict sales for the future data
future_df['Predicted_Sales1'] = model.predict(X_future)

# Save the future_df to a CSV file
future_df.to_csv('attempt2_3month_predictions.csv', index=False)
