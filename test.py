# import pandas as pd
# import numpy as np
# import mysql.connector
# from mysql.connector import Error
# from sklearn.preprocessing import LabelEncoder
# from xgboost import XGBClassifier


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


# sql_query_extract = '''
# SELECT * FROM BM_FactCustomers LIMIT 1;
# '''

# # Fetch data
# mydb, cursor = get_db_connection()
# cursor.execute(sql_query_extract)
# data = cursor.fetchall()
# columns = [i[0] for i in cursor.description]  # Get column names

# # Convert to DataFrame
# df = pd.DataFrame(data, columns=columns)

# # Only extract the needed features
# features = df.drop(columns=['subscribed_y', 'duration','customer_id'])

# # Values to inserted in dataframe, will come fron front-end in the future.
# user_input = {
#     'age': 35,  # Example age
#     'job': 'tertiary',  # Example job
#     'marital': 'married',  # Example marital status
#     'education': 'university',  # Example education level
#     'default_credit': 'no',  # Has credit in default?
#     'balance': 2345.0,  # Account balance
#     'housing': 'yes',  # Has housing loan?
#     'loan': 'no',  # Has personal loan?
#     'contact': 'cellular',  # Contact communication type
#     'month': 'jul',  # Last contact month of year
#     'campaign': 3,  # Number of contacts performed during this campaign and for this client
#     'pdays': 999,  # Number of days that passed by after the client was last contacted from a previous campaign (999 means client was not previously contacted)
#     'previous': 1,  # Number of contacts performed before this campaign and for this client
#     'poutcome': 'success'  # Outcome of the previous marketing campaign
# }

# # adding user_input
# features.loc[0] = pd.Series(user_input)

# # Convert ENUM and other categorical data to category type for better memory usage and performance
# for col in features.columns:
#     if features[col].dtype == 'object':  # This will catch both ENUM and VARCHAR
#         features[col] = features[col].astype('category')

# # Encode categorical variables
# le = LabelEncoder()
# for column in features.select_dtypes(include=['category', 'object']):
#     features[column] = le.fit_transform(features[column])

# print(features.head())

# # Import the model
# model = xgb.XGBRegressor()
# model.load_model('bank_marketing/ml_model_classification_bank_marketing.json')

# # Apply the model to the data
# X = df[features]
# predictions = model.predict(X)
# predictions = 0

# # Convert predictions to a DataFrame if it's not already one
# final_prediction = 'yes' if predictions[0] == 1 else 'no'

import time
import re
import csv
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
import os

start_readingdata = time.time()

# Define metrics and get selected performance measure
metrics = ['RMSE', 'MSE', 'MAE', 'MAPE', 'AVG % difference from actual']
selected_performance_measure = 'RMSE'

# Read and filter performance data directly during loading
performance_data = pd.read_csv('online_retail/performancemeasures_mlmodel_online_retail.csv')
filtered_performance_data = performance_data[performance_data.iloc[:, 1] == selected_performance_measure]
performance_data = list(filtered_performance_data.itertuples(index=False, name=None))

# Query actual sales data from database using a context manager for efficient connection handling
sales_per_day_sql = '''
    SELECT
        InvoiceDate,
        SUM(Total_Actual_Sales) AS Total_Actual_Sales
    FROM
        ONR_DimInvoice AS inv
    JOIN
        ONR_FactTransactions AS trans ON inv.InvoiceID = trans.InvoiceID
    GROUP BY
        InvoiceDate
    ORDER BY
        InvoiceDate;
'''

end_readingdata = time.time()
print(f"Time taken to read data: {end_readingdata - start_readingdata} seconds")

start_executingquery = time.time()

# Connect to MySQL database
mydb, cursor = get_db_connection()
cursor.execute(sales_per_day_sql)
actual_sales_per_day = cursor.fetchall()

end_executingquery = time.time()
print(f"Time taken to execute query: {end_executingquery - start_executingquery} seconds")

start_convertingdata = time.time()

# Convert SQL query result to DataFrame and ensure date formatting
actual_sales_df = pd.DataFrame(actual_sales_per_day, columns=['InvoiceDate', 'Total_Actual_Sales'])
actual_sales_df['InvoiceDate'] = pd.to_datetime(actual_sales_df['InvoiceDate'])

# Load and filter the prediction data more efficiently
prediction_df = pd.read_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv', usecols=lambda col: col == 'InvoiceDate' or col.startswith('Total_Predicted_Sales'))
prediction_df['InvoiceDate'] = pd.to_datetime(prediction_df['InvoiceDate'])

# Ensure both DataFrames are sorted by InvoiceDate
actual_sales_df.sort_values('InvoiceDate', inplace=True)
prediction_df.sort_values('InvoiceDate', inplace=True)

# Merge DataFrames, keeping all dates from both sides
merged_df = pd.merge(actual_sales_df, prediction_df, on='InvoiceDate', how='outer')

# Reorder columns and handle missing data
columns_order = ['InvoiceDate', 'Total_Actual_Sales'] + [col for col in merged_df.columns if col.startswith('Total_Predicted_Sales')]
merged_df = merged_df[columns_order]
# Replace NaN values with None (null in JSON)
merged_df = merged_df.replace({np.nan: None})

# Format 'InvoiceDate' to ISO 8601 (YYYY-MM-DD) for JSON
merged_df['InvoiceDate'] = merged_df['InvoiceDate'].dt.strftime('%Y-%m-%d')

# Convert to dictionary for JSON serialization
sales_data = merged_df.to_dict('records')

end_convertingdata = time.time()
print(f"Time taken to convert data: {end_convertingdata - start_convertingdata} seconds")
