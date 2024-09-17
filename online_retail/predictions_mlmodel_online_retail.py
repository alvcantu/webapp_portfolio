import pandas as pd
import numpy as np
import datetime
import mysql.connector
from datetime import datetime
import random
import joblib
from sklearn.preprocessing import LabelEncoder

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

# Create new dataframe with future dates
transaction_pivoted_df = pd.DataFrame({'InvoiceDate': future_dates})

# Convert to valid data types
transaction_pivoted_df['InvoiceDate'] = pd.to_datetime(transaction_pivoted_df['InvoiceDate'])

# Feature Engineering
transaction_pivoted_df['Year'] = transaction_pivoted_df['InvoiceDate'].dt.year
transaction_pivoted_df['Month'] = transaction_pivoted_df['InvoiceDate'].dt.month
transaction_pivoted_df['Day'] = transaction_pivoted_df['InvoiceDate'].dt.day
transaction_pivoted_df['DayOfWeek'] = transaction_pivoted_df['InvoiceDate'].dt.dayofweek
transaction_pivoted_df['IsWeekend'] = transaction_pivoted_df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
transaction_pivoted_df['Quarter'] = transaction_pivoted_df['InvoiceDate'].dt.quarter
transaction_pivoted_df['Season'] = transaction_pivoted_df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else 
                                         'Spring' if x in [3, 4, 5] else 
                                         'Summer' if x in [6, 7, 8] else 'Autumn')
transaction_pivoted_df['WeekOfMonth'] = transaction_pivoted_df['InvoiceDate'].apply(lambda x: (x.day - 1) // 7 + 1)                                         
# Assuming your fiscal year starts in July
transaction_pivoted_df['FiscalQuarter'] = transaction_pivoted_df['Month'].apply(lambda x: (x - 7) % 12 // 3 + 1)
transaction_pivoted_df['FiscalYear'] = transaction_pivoted_df['Year'] + transaction_pivoted_df['Month'].apply(lambda x: 1 if x >= 7 else 0)

# Label encoding Season feature
le = LabelEncoder()
transaction_pivoted_df['Season'] = le.fit_transform(transaction_pivoted_df['Season'])

# Features trasaction model was trained on
features = transaction_pivoted_df[['Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear']]

# Apply transactions model to the future dates
transactions_model = joblib.load('online_retail/transactions_count_mlmodel_online_retail.joblib')
transactions_pred = transactions_model.predict(features)
# Add the predicted transactions to the future dataframe
transaction_pivoted_df['distinct_transactions'] = transactions_pred

# Drop all columns from transaction_pivoted_df except InvoiceDate and distinct_transactions
transaction_pivoted_df = transaction_pivoted_df.drop(columns=['Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear'])

# Create a new DataFrame by repeating 'InvoiceDate' based on 'distinct_transactions'
expanded_df = transaction_pivoted_df.loc[transaction_pivoted_df.index.repeat(transaction_pivoted_df['distinct_transactions'])].copy()

# Reset index and keep only 'InvoiceDate'
expanded_df = expanded_df[['InvoiceDate']].reset_index(drop=True)

# Get unique valid combinations of CustomerID, StockCode, and Country from the historical data
valid_combinations = df[['CustomerID', 'StockCode', 'Country']].drop_duplicates()

# Initialize an empty list to hold the future data
future_data = []

# Count of transactions for each date in expanded_df
date_counts = expanded_df['InvoiceDate'].value_counts().sort_index()

# Add random values if valud combinations for each new date in expanded_df
for date in future_dates:
    # Check if this date exists in expanded_df, if not, skip or handle as needed
    if date not in date_counts:
        print(f"Warning: Date {date} not found in expanded data. Skipping.")
        continue
    
    # Get the number of rows for this date
    sample_size = date_counts[date]
    
    # Randomly sample valid combinations for this date
    sampled_combinations = valid_combinations.sample(n=sample_size, replace=True)
    
    # Create future data for each sampled combination
    for _, row in sampled_combinations.iterrows():
        customer_id = row['CustomerID']
        stock_code = row['StockCode']
        country = row['Country']
        
        future_data.append({
            'InvoiceID': np.nan,  
            'CustomerID': customer_id,
            'InvoiceDate': date,  
            'Country': country,
            'StockCode': stock_code,
            'Description': np.nan,  
            'Quantity': np.nan,     
            'UnitPrice': np.nan,    
            'Sales': np.nan         
        })

# Convert the list of dictionaries to a DataFrame
transaction_df = pd.DataFrame(future_data).reset_index(drop=True)

# Save the transaction_pivoted_df to a CSV file
transaction_df.to_csv('online_retail/online_retail_3month_predictions.csv', index=False)
# Save the transaction_pivoted_df to a CSV file
transaction_pivoted_df.to_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv', index=False)

