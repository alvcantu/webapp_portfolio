import pandas as pd
import numpy as np
import datetime
import mysql.connector
from datetime import datetime
import random

# Script creates sample data for the next 3 months for prediction models can be applied to it.

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

import pandas as pd
import numpy as np

# Execute the original query
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

# Find the last InvoiceDate in your current data
last_date = df['InvoiceDate'].max()

# Create future dates for the next 3 months
num_months = 3
future_dates = pd.date_range(last_date + pd.DateOffset(1), periods=num_months*30, freq='D')

# Get unique valid combinations of CustomerID, StockCode, and Country from the historical data
valid_combinations = df[['CustomerID', 'StockCode', 'Country']].drop_duplicates()

# Initialize an empty list to hold the future data
future_data = []

# For each future date, randomly sample from the valid combinations and create feature rows
sample_size = 1776  # Using the average # of transactions per day for the whole dataset as sample size 

for date in future_dates:
    # Randomly sample valid combinations for this date
    sampled_combinations = valid_combinations.sample(n=sample_size, replace=False)
    
    # Create future data for each sampled combination
    for _, row in sampled_combinations.iterrows():
        customer_id = row['CustomerID']
        stock_code = row['StockCode']
        country = row['Country']
        
        future_data.append({
            'InvoiceID': np.nan,  # InvoiceID will be NaN for future data
            'CustomerID': customer_id,
            'InvoiceDate': date,  # Use the current future date
            'Country': country,
            'StockCode': stock_code,
            'Description': np.nan,  # Set Description as NaN
            'Quantity': np.nan,     # Set Quantity as NaN
            'UnitPrice': np.nan,    # Set UnitPrice as NaN
            'Sales': np.nan         # Sales will be NaN since Quantity * UnitPrice is undefined
        })

# Convert the future data into a DataFrame
future_df = pd.DataFrame(future_data)

# Save the future_df to a CSV file
future_df.to_csv('online_retail/online_retail_3month_predictions.csv', index=False)

