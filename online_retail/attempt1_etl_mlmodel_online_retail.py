import pandas as pd
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb

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

# Future df processing
future_df_og = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_pivoted_perday = pd.read_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv')

# # Convert to valid data types
# df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
# df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')
# # Feature Engineering
# df['Year'] = df['InvoiceDate'].dt.year
# df['Month'] = df['InvoiceDate'].dt.month
# df['Day'] = df['InvoiceDate'].dt.day
# df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
# df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')

# # Encode categorical variables
# le = LabelEncoder()
# df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
# df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
# df['Country'] = le.fit_transform(df['Country'])

# Convert to valid data types
future_df['InvoiceDate'] = pd.to_datetime(future_df['InvoiceDate'])
future_df['UnitPrice'] = future_df['UnitPrice'].fillna(0).astype('float32')
# Feature Engineering
future_df['Year'] = future_df['InvoiceDate'].dt.year
future_df['Month'] = future_df['InvoiceDate'].dt.month
future_df['Day'] = future_df['InvoiceDate'].dt.day
future_df['DayOfWeek'] = future_df['InvoiceDate'].dt.dayofweek
future_df['UnitPrice'] = future_df['UnitPrice'].fillna(0).astype('float32')

# Encode categorical variables
le = LabelEncoder()
future_df['CustomerID'] = le.fit_transform(future_df['CustomerID'].astype(str))
future_df['StockCode'] = le.fit_transform(future_df['StockCode'].astype(str))
future_df['Country'] = le.fit_transform(future_df['Country'])

# # Features the model was trained on
features = ['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt1_xgboost_mlmodel_online_retail.json')

# Make predictions
# Only using features in the training set
# For original data
# X = df[features]
# predictions = model.predict(X)
# For future data
X_future = future_df[features]
predictions_future = model.predict(X_future)

# Adding column with predictes sales to the original dataframe
# df['Predicted_Sales1'] = predictions
# Adding column with future sales predictions
future_df_og['Predicted_Sales1'] = predictions_future

# Converting Predicted_Sales1 to float and rounding to two decimal places
# df['Predicted_Sales1'] = df['Predicted_Sales1'].astype(float)
# df['Predicted_Sales1'] = df['Predicted_Sales1'].round(2)
# Converting Predicted_Sales1 to float and rounding to two decimal places
future_df_og['Predicted_Sales1'] = future_df_og['Predicted_Sales1'].astype(float)
future_df_og['Predicted_Sales1'] = future_df_og['Predicted_Sales1'].round(2)

# Save future_df to a CSV file
future_df_og.to_csv('online_retail/online_retail_3month_predictions.csv', index=False)

# Pivot the future_df to get Predicted_Sales1 per InvoiceDate and save it to a CSV file
future_df_pivoted = pd.pivot_table(future_df_og, 
                          values='Predicted_Sales1', 
                          index='InvoiceDate', 
                          aggfunc='sum')

# Ensure both DataFrames are sorted by this InvoiceDate:
future_df_pivoted_perday = future_df_pivoted_perday.sort_index() 
future_df_pivoted = future_df_pivoted.sort_index()
future_df_pivoted_perday.reset_index(inplace=True)
future_df_pivoted.reset_index(inplace=True)
# Insert Predicted_Sales1 column into the pivoted DataFrame
future_df_pivoted_perday['Total_Predicted_Sales1'] = future_df_pivoted['Predicted_Sales1']
# Save the pivoted DataFrame to original CSV file
future_df_pivoted_perday.to_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv', index=False)

# # Filtering df so it has only InvoiceID and Predicted_Sales columns
# df_to_insert = df[['TransactionID', 'Predicted_Sales1']]

# print(df_to_insert.head())

# # SQL to delete the column if it exists
# delete_column_sql = """
# ALTER TABLE ONR_FactTransactions 
# DROP COLUMN Predicted_Sales1;
# """

# # SQL to add the column if it doesn't exist
# add_column_sql = """
# ALTER TABLE ONR_FactTransactions 
# ADD COLUMN Predicted_Sales1 FLOAT;
# """

# # SQL to update the comment for the new column
# update_comment_sql = """
# ALTER TABLE ONR_FactTransactions 
# MODIFY COLUMN Predicted_Sales1 FLOAT COMMENT 'Predicted sales (UnitPrice * Quantity) with second machine learning model using XGBoost and Bayesian Optimization.';
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
#     INSERT INTO ONR_FactTransactions (TransactionID, Predicted_Sales1)
#     VALUES (%s, %s)
#     ON DUPLICATE KEY UPDATE Predicted_Sales1 = VALUES(Predicted_Sales1);
#     """

#     # Convert DataFrame to a list of tuples for executemany
#     data_to_insert = list(zip(df_to_insert['TransactionID'], df_to_insert['Predicted_Sales1']))

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