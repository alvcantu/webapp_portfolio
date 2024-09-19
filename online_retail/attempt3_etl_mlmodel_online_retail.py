import pandas as pd
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
import holidays

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

# Function to check if it's a holiday
def is_holiday(row):
    country_code = row['holiday_code']
    invoice_date = row['InvoiceDate'].date()  # Get the date part
    
    # Create the holiday calendar for the specified country
    try:
        country_holidays = holidays.CountryHoliday(country_code)
        return True in country_holidays  # Check if the date is a holiday
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

# Load the CSV with country to holiday_code mapping
country_code_df = pd.read_csv('online_retail/country_mapping_online_retail.csv')
# Merge the dataframes to get the holiday_code, 
# Mapping assumes all not available countires in holidays as part of Great Britain given its a UK online ratailer
df = pd.merge(df, country_code_df, on='Country', how='left')

# Future df processing
future_df = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_og = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_pivoted_perday = pd.read_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv')

future_df = pd.merge(future_df, country_code_df, on='Country', how='left')

# Convert to valid data types
future_df['InvoiceDate'] = pd.to_datetime(future_df['InvoiceDate'])

# Feature Engineering of InvoiceDate
future_df['Year'] = future_df['InvoiceDate'].dt.year
future_df['Month'] = future_df['InvoiceDate'].dt.month # Assuming your fiscal year starts in July
future_df['Month'] = future_df['InvoiceDate'].dt.month
future_df['Day'] = future_df['InvoiceDate'].dt.day
future_df['DayOfWeek'] = future_df['InvoiceDate'].dt.dayofweek
future_df['IsWeekend'] = future_df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
future_df['Quarter'] = future_df['InvoiceDate'].dt.quarter
future_df['Season'] = future_df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else
                                         'Spring' if x in [3, 4, 5] else
                                         'Summer' if x in [6, 7, 8] else 'Autumn')
future_df['WeekOfMonth'] = future_df['InvoiceDate'].apply(lambda x: (x.day - 1) // 7 + 1)
# Assuming your fiscal year starts in July
future_df['FiscalQuarter'] = future_df['Month'].apply(lambda x: (x - 7) % 12 // 3 + 1)
future_df['FiscalYear'] = future_df['Year'] + future_df['Month'].apply(lambda x: 1 if x >= 7 else 0)
# Apply the function to create the 'IsHoliday' column
future_df['holiday_code'] = future_df['holiday_code'].astype(str)
future_df['IsHoliday'] = future_df.apply(is_holiday, axis=1)

# Additional feature engineering
# Categoize StockCodes
future_df['StockCodeCategory'] = future_df['StockCode'].apply(categorize_stockcode)
future_df['StockCodeLength'] = future_df['StockCode'].str.len()

# Encode categorical variables
le = LabelEncoder()
future_df['CustomerID'] = le.fit_transform(future_df['CustomerID'].astype(str))
future_df['StockCode'] = le.fit_transform(future_df['StockCode'].astype(str))
future_df['Country'] = le.fit_transform(future_df['Country'])
future_df['Season'] = le.fit_transform(future_df['Season'])
future_df['Description'] = le.fit_transform(future_df['Description'])
future_df['StockCodeCategory'] = le.fit_transform(future_df['StockCodeCategory'])
future_df['continent'] = le.fit_transform(future_df['continent'])


# # Convert to valid data types
# df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

# # Feature Engineering of InvoiceDate
# df['Year'] = df['InvoiceDate'].dt.year
# df['Month'] = df['InvoiceDate'].dt.month
# df['Day'] = df['InvoiceDate'].dt.day
# df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
# df['IsWeekend'] = df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
# df['Quarter'] = df['InvoiceDate'].dt.quarter
# df['Season'] = df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else
#                                          'Spring' if x in [3, 4, 5] else
#                                          'Summer' if x in [6, 7, 8] else 'Autumn')
# df['WeekOfMonth'] = df['InvoiceDate'].apply(lambda x: (x.day - 1) // 7 + 1)
# # Assuming your fiscal year starts in July
# df['FiscalQuarter'] = df['Month'].apply(lambda x: (x - 7) % 12 // 3 + 1)
# df['FiscalYear'] = df['Year'] + df['Month'].apply(lambda x: 1 if x >= 7 else 0)
# # Apply the function to create the 'IsHoliday' column
# df['holiday_code'] = df['holiday_code'].astype(str)
# df['IsHoliday'] = df.apply(is_holiday, axis=1)

# # Additional feature engineering
# # Categoize StockCodes
# df['StockCodeCategory'] = df['StockCode'].apply(categorize_stockcode)
# df['StockCodeLength'] = df['StockCode'].str.len()

# # Encode categorical variables
# le = LabelEncoder()
# df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
# df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
# df['Country'] = le.fit_transform(df['Country'])
# df['Season'] = le.fit_transform(df['Season'])
# df['Description'] = le.fit_transform(df['Description'])
# df['StockCodeCategory'] = le.fit_transform(df['StockCodeCategory'])
# df['continent'] = le.fit_transform(df['continent'])

# Features the model was trained on
features = ['CustomerID', 'StockCode', 'Country', 'Description', 'StockCodeCategory', 'continent', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear', 'IsHoliday', 'StockCodeLength']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt3_xgboost_mlmodel_online_retail.json')

# Make predictions
# Only using features in the training set
# For original data
# X = df[features]
# predictions = model.predict(X)
# For future data
X_future = future_df[features]
predictions_future = model.predict(X_future)

# Adding column with predictes sales to the original dataframe
# df['Predicted_Sales3'] = predictions
# Adding column with future sales predictions
future_df_og['Predicted_Sales3'] = predictions_future

# Converting Predicted_Sales3 to float and rounding to two decimal places
# df['Predicted_Sales3'] = df['Predicted_Sales3'].astype(float)
# df['Predicted_Sales3'] = df['Predicted_Sales3'].round(2)
# Converting Predicted_Sales3 to float and rounding to two decimal places
future_df_og['Predicted_Sales3'] = future_df_og['Predicted_Sales3'].astype(float)
future_df_og['Predicted_Sales3'] = future_df_og['Predicted_Sales3'].round(2)

# Save future_df to a CSV file
future_df_og.to_csv('online_retail/online_retail_3month_predictions.csv', index=False)

# Pivot the future_df to get Predicted_Sales1 per InvoiceDate and save it to a CSV file
future_df_pivoted = pd.pivot_table(future_df_og,
                          values='Predicted_Sales3',
                          index='InvoiceDate',
                          aggfunc='sum')

# Ensure both DataFrames are sorted by this InvoiceDate:
future_df_pivoted_perday = future_df_pivoted_perday.sort_index()
future_df_pivoted = future_df_pivoted.sort_index()
# Drop level 0 column from pivoted DataFrame
future_df_pivoted_perday.drop(columns=['level_0'], inplace=True)
future_df_pivoted.reset_index(inplace=True)
# Insert Predicted_Sales1 column into the pivoted DataFrame
future_df_pivoted_perday['Total_Predicted_Sales3'] = future_df_pivoted['Predicted_Sales3']

print(future_df_pivoted_perday.head())
# Save the pivoted DataFrame to original CSV file
future_df_pivoted_perday.to_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv', index=False)

# # Filtering df so it has only InvoiceID and Predicted_Sales columns
# df_to_insert = df[['TransactionID', 'Predicted_Sales3']]

# # # SQL to delete the column if it exists
# delete_column_sql = """
# ALTER TABLE ONR_FactTransactions
# DROP COLUMN Predicted_Sales3;
# """

# # SQL to add the column if it doesn't exist
# add_column_sql = """
# ALTER TABLE ONR_FactTransactions
# ADD COLUMN Predicted_Sales3 FLOAT;
# """

# # SQL to update the comment for the new column
# update_comment_sql = """
# ALTER TABLE ONR_FactTransactions
# MODIFY COLUMN Predicted_Sales3 FLOAT COMMENT 'Predicted sales (UnitPrice * Quantity) with third machine learning model using XGBoost and Bayesian Optimization.';
# """

# # Adding new predicted sales column to ONR_FactTransactions table in mysql
# mydb, cursor = get_db_connection()
# #cursor.execute(delete_column_sql)
# cursor.execute(add_column_sql)
# cursor.execute(update_comment_sql)
# mydb.commit()  # Commit the transaction for schema changes

# # SQL to insert the new column into the table
# try:
#     # Your SQL statement
#     update_sql = """
#     INSERT INTO ONR_FactTransactions (TransactionID, Predicted_Sales3)
#     VALUES (%s, %s)
#     ON DUPLICATE KEY UPDATE Predicted_Sales3 = VALUES(Predicted_Sales3);
#     """

#     # Convert DataFrame to a list of tuples for executemany
#     data_to_insert = list(zip(df_to_insert['TransactionID'], df_to_insert['Predicted_Sales3']))

#     # Execute the query with many parameters
#     cursor.executemany(update_sql, data_to_insert)

#     # Commit the transaction
#     mydb.commit()

#     print(f"{cursor.rowcount} records were successfully inserted or updated.")

# except Error as error:
#     print(f"Failed to insert data into MySQL table {error}")
#     mydb.rollback()  # Rollback in case of error

# finally:
#     # Closing the connection
#     if mydb.is_connected():
#         cursor.close()
#         mydb.close()
#         print("MySQL connection is closed")