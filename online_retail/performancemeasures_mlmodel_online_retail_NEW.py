import csv
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
import xgboost as xgb
import json
from sklearn.preprocessing import LabelEncoder
import holidays
from mysql.connector import Error

# Script that generates performance measures for the all machine learning regression models for all Predicted_Sales columns in mySQL

# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor()
    return mydb, cursor

# Connect to MySQL database
mydb, cursor = get_db_connection()


# Extract all transactions from the database
query = '''
SELECT 
    t.TransactionID AS TransactionID,
    i.CustomerID AS CustomerID,
    i.InvoiceDate AS InvoiceDate,
    i.Country AS Country,
    t.StockCode AS StockCode,
    t.Description AS Description,
    (t.Quantity * t.UnitPrice) AS Sales
FROM 
    ONR_FactTransactions t
JOIN 
    ONR_DimInvoice i ON t.InvoiceID = i.InvoiceID;
'''

# Execute the query
mydb, cursor = get_db_connection()
cursor.execute(query)
# Fetch all rows as a list of dictionaries where keys are column names
rows = cursor.fetchall()
# Convert the list of dictionaries to a DataFrame
df = pd.DataFrame(rows)

# Ensure the DataFrame has the correct column headers
df.columns = [desc[0] for desc in cursor.description]

# Load the CSV with country to holiday_code mapping
country_code_df = pd.read_csv('/home/alvcantu/online_retail/country_mapping_online_retail.csv')
# Merge the dataframes to get the holiday_code, 
# Mapping assumes all not available countires in holidays as part of Great Britain given its a UK online ratailer
df = pd.merge(df, country_code_df, on='Country', how='left')

# Time-based split, 70% for training, 30% for testing
train_size = int(len(df) * 0.7)
train_df = df.iloc[:train_size]

print(train_df.head())

# Function to check if it's a holiday
def is_holiday(row):
    country_code = row['holiday_code']
    invoice_date = row['InvoiceDate'].date()  # Get the date part
    
    # Create the holiday calendar for the specified country
    try:
        country_holidays = holidays.CountryHoliday(country_code)
        return invoice_date in country_holidays  # Check if the date is a holiday
    except KeyError:
        return False  # If the country code is not supported by the holidays library

# Function to categorize StockCode
def categorize_stockcode(code):
    if code == 'AMAZONFEE' or code == 'BANK CHARGES':
        return 'Fees or bank charges'
    elif code.startswith('DCGSS'):
        return 'party bags'
    elif code.startswith('gift'):
        return 'gift'
    elif code == 'DOT' or code == 'POST':
        return 'Postage costs'
    else:
        return 'Not-classified'

# Feature engineering function
def feature_engineering(df, attempt):
    # Convert to valid data types
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

    # Feature Engineering of InvoiceDate
    df['Year'] = df['InvoiceDate'].dt.year
    df['Month'] = df['InvoiceDate'].dt.month
    df['Day'] = df['InvoiceDate'].dt.day
    df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
    df['IsWeekend'] = df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
    df['Quarter'] = df['InvoiceDate'].dt.quarter
    df['Season'] = df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else 
                                             'Spring' if x in [3, 4, 5] else 
                                             'Summer' if x in [6, 7, 8] else 'Autumn')
    df['WeekOfMonth'] = df['InvoiceDate'].apply(lambda x: (x.day - 1) // 7 + 1)                                         
    # Assuming your fiscal year starts in July
    df['FiscalQuarter'] = df['Month'].apply(lambda x: (x - 7) % 12 // 3 + 1)
    df['FiscalYear'] = df['Year'] + df['Month'].apply(lambda x: 1 if x >= 7 else 0)
    # Apply the function to create the 'IsHoliday' column
    df['holiday_code'] = df['holiday_code'].astype(str)
    df['IsHoliday'] = df.apply(is_holiday, axis=1)

    # Additional feature engineering
    # Categorize StockCodes
    df['StockCodeCategory'] = df['StockCode'].apply(categorize_stockcode)
    df['StockCodeLength'] = df['StockCode'].str.len()

    # Encode categorical variables
    le = LabelEncoder()
    df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
    df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
    df['Country'] = le.fit_transform(df['Country'])
    df['Season'] = le.fit_transform(df['Season'])
    df['Description'] = le.fit_transform(df['Description'])
    df['StockCodeCategory'] = le.fit_transform(df['StockCodeCategory'])
    df['continent'] = le.fit_transform(df['continent'])

    # Select features based on attempt
    if attempt == 2:
        X = df[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'Country']]
    elif attempt == 3 or attempt == 4:
        X = df[['CustomerID', 'StockCode', 'Country', 'Description', 'StockCodeCategory', 'continent', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear', 'IsHoliday', 'StockCodeLength']]
    return X

# Apply the models and insert predictions into the database
for x in range(2, 5):
    json_file = f'/home/alvcantu/online_retail/attempt{x}_xgboost_mlmodel_online_retail.json'
    
    # Apply feature engineering
    X = feature_engineering(train_df, x)
    
    # Load the model from JSON
    with open(json_file, 'r') as f:
        model_json = json.load(f)
    
    # Convert JSON to XGBoost model
    model = xgb.Booster(model_file=json_file)
    
    # Prepare the data for prediction
    dmatrix = xgb.DMatrix(X)
    
    # Make predictions
    predictions = model.predict(dmatrix)
    
    # Add predictions to the DataFrame
    train_df[f'Predicted_Sales{x}'] = predictions
    
    # Filtering df so it has only TransactionID and Predicted_Sales columns
    df_to_insert = train_df[['TransactionID', f'Predicted_Sales{x}']]
    
    # SQL to delete the column if it exists
    # delete_column_sql = f"""
    # ALTER TABLE ONR_FactTransactions
    # DROP COLUMN IF EXISTS Predicted_Sales{x};
    # """
    
    # SQL to add the column if it doesn't exist
    add_column_sql = f"""
    ALTER TABLE ONR_FactTransactions
    ADD COLUMN Predicted_Sales{x} FLOAT;
    """
    
    # SQL to update the comment for the new column
    update_comment_sql = f"""
    ALTER TABLE ONR_FactTransactions
    MODIFY COLUMN Predicted_Sales{x} FLOAT COMMENT 'Predicted sales (UnitPrice * Quantity) with attempt {x} machine learning model using XGBoost to testing data only.';
    """
    
    # Adding new predicted sales column to ONR_FactTransactions table in mysql
    # cursor.execute(delete_column_sql)
    cursor.execute(add_column_sql)
    cursor.execute(update_comment_sql)
    mydb.commit()  # Commit the transaction for schema changes
    
    # SQL to insert the new column into the table
    try:
        # Your SQL statement
        update_sql = f"""
        INSERT INTO ONR_FactTransactions (TransactionID, Predicted_Sales{x})
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE Predicted_Sales{x} = VALUES(Predicted_Sales{x});
        """
    
        # Convert DataFrame to a list of tuples for executemany
        data_to_insert = list(zip(df_to_insert['TransactionID'], df_to_insert[f'Predicted_Sales{x}']))
    
        # Execute the query with many parameters
        cursor.executemany(update_sql, data_to_insert)
    
        # Commit the transaction
        mydb.commit()
    
        print(f"{cursor.rowcount} records were successfully inserted or updated for attempt {x}.")
    
    except Error as error:
        print(f"Failed to insert data into MySQL table for attempt {x}: {error}")
        mydb.rollback()  # Rollback in case of error


# SQL query that returns all column names of predicted sales for all models
column_names_sql = '''
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'ONR_FactTransactions'
    AND column_name LIKE 'Predicted_Sales%';
'''
# Fetch column names
cursor.execute(column_names_sql)
column_names = [row[0] for row in cursor.fetchall()]

# Function to generate SQL for each metric and column combination
def generate_sql(metrics, column_names):
    sql_parts = []
    
    # Loop through each metric
    for metric in metrics:
        # Loop through each column name
        for col in column_names:
            sql_parts.append(f'''
                SELECT '{col}' AS prediction_type, '{metric}' AS metric, {dynamic_sqls[metric].format(col=col)} AS value
                FROM ONR_FactTransactions
            ''')

    # Ensure there's at least one part
    if not sql_parts:
        return ""
    
    # Join with UNION ALL between all parts
    return ' UNION ALL '.join(sql_parts) + ';'

# Define metrics
metrics = ['RMSE', 'MSE', 'MAE', 'MAPE', 'AVG % difference from actual']

# Define dynamic SQL for each metric
dynamic_sqls = {
    'RMSE': 'ROUND(SQRT(AVG(POWER((Quantity * UnitPrice) - {col}, 2))), 2)',
    'MSE': 'ROUND(SUM(POW((UnitPrice * Quantity) - {col}, 2)) / COUNT(*), 2)',
    'MAE': 'ROUND(AVG(ABS((UnitPrice * Quantity) - {col})), 2)',
    'MAPE': 'ROUND((SUM(ABS((Quantity * UnitPrice) - {col}) / NULLIF(Quantity * UnitPrice, 0)) / COUNT(*)) * 100, 2)',
    'AVG % difference from actual': 'ROUND(AVG(ABS(({col} - (Quantity * UnitPrice)) / (Quantity * UnitPrice)) * 100), 2)'
}

# Generate the SQL
sql = generate_sql(metrics, column_names)

# Execute the generated SQL
cursor.execute(sql)
performance_data = cursor.fetchall()

# Add the header row to the data
header = [['column_name', 'performance_metric', 'value']]  # This is the new header row
performance_data = header + performance_data

# Save performance_data as csv 
with open('online_retail/performancemeasures_NEW_mlmodel_online_retail.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(performance_data)

# Close database connection
cursor.close()
mydb.close()