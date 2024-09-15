# # test
import pandas as pd
import mysql.connector
import numpy as np

# # Extract total sales per day from prediction csv
# # Read prediction csv
# prediction_df = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
# # Convert to valid data types
# prediction_df['InvoiceDate'] = pd.to_datetime(prediction_df['InvoiceDate'])
# # Group by InvoiceDate and sum all columns starting with 'Predicted_Sales'
# columns_to_sum = [col for col in prediction_df.columns if col.startswith('Predicted_Sales')]
# grouped_df = prediction_df.groupby('InvoiceDate')[columns_to_sum].sum().reset_index()

# # Rename columns for clarity
# grouped_df = grouped_df.rename(columns={col: f'Total_{col}' for col in columns_to_sum})

# # Connect to MySQL database
# def get_db_connection():
#     mydb = mysql.connector.connect(
#         host="alvcantu.mysql.pythonanywhere-services.com",
#         user="alvcantu",
#         password="h63Efp09-d",
#         database="alvcantu$default"
#     )
#     cursor = mydb.cursor()
#     return mydb, cursor

# # Connect to MySQL database
# mydb, cursor = get_db_connection()

# # Query to extract total sales per day
# sales_per_day_sql = '''
#     SELECT
#         DATE(InvoiceDate) AS InvoiceDate,
#         SUM(Quantity * UnitPrice) AS Total_Actual_Sales
#     FROM
#         ONR_DimInvoice AS inv
#     JOIN
#         ONR_FactTransactions AS trans ON inv.InvoiceID = trans.InvoiceID
#     GROUP BY
#         DATE(InvoiceDate)
#     ORDER BY
#         Total_Actual_Sales
#     '''

# cursor.execute(sales_per_day_sql)
# actual_sales_per_day = cursor.fetchall()

# # Convert SQL query result to DataFrame
# actual_sales_df = pd.DataFrame(actual_sales_per_day, columns=['InvoiceDate', 'Total_Actual_Sales'])
# actual_sales_df['InvoiceDate'] = pd.to_datetime(actual_sales_df['InvoiceDate'])

# # Ensure both DataFrames are sorted by InvoiceDate
# grouped_df = grouped_df.sort_values('InvoiceDate')
# actual_sales_df = actual_sales_df.sort_values('InvoiceDate')

# # Merge the DataFrames on InvoiceDate
# # We'll use merge instead of concat to handle potential date mismatches
# merged_df = pd.merge(
#     actual_sales_df,
#     grouped_df,
#     on='InvoiceDate',
#     how='outer'  # Use 'outer' if you want to keep all dates from both DataFrames
# )

# # Reorder columns to have InvoiceDate first, then Total_Actual_Sales, followed by Total_Predicted_Sales columns
# columns_order = ['InvoiceDate', 'Total_Actual_Sales'] + [col for col in merged_df.columns if col.startswith('Total_Predicted_Sales')]
# merged_df = merged_df[columns_order]

# # Filter the dataframe to include only rows where Total_Predicted_Sales2 is not NaN
# filtered_df = merged_df[merged_df['Total_Predicted_Sales2'].notna()]

# # Add a new column 'avgsalespertransaction'
# filtered_df['avgsalespertransaction'] = filtered_df['Total_Predicted_Sales2'] / 1776

# # Select only the desired columns
# result_df = filtered_df[['InvoiceDate', 'Total_Actual_Sales', 'Total_Predicted_Sales2', 'avgsalespertransaction']]

# # Print out the dataframe
# print(result_df.head())

# print("Average avgsalespertransaction:")
# print(result_df['avgsalespertransaction'].mean())
# print("Median avgsalespertransaction:")
# print(result_df['avgsalespertransaction'].median())
# print("Standard deviation avgsalespertransaction:")
# print(result_df['avgsalespertransaction'].std())
# print("Minimum avgsalespertransaction:")
# print(result_df['avgsalespertransaction'].min())
# print("Maximum avgsalespertransaction:")
# print(result_df['avgsalespertransaction'].max())

# # Close connection
# cursor.close()
# mydb.close()

# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor(dictionary=True)
    return mydb, cursor

# Connect to MySQL database
mydb, cursor = get_db_connection()

# Back-end for second chart.js showing actual and predicted sales per day, sales_data is pushed to front-end
# Query to extract total sales per day
sales_per_day_sql = '''
    SELECT
        DATE(InvoiceDate) AS InvoiceDate,
        SUM(Quantity * UnitPrice) AS Total_Actual_Sales
    FROM
        ONR_DimInvoice AS inv
    JOIN
        ONR_FactTransactions AS trans ON inv.InvoiceID = trans.InvoiceID
    GROUP BY
        DATE(InvoiceDate)
    ORDER BY
        Total_Actual_Sales
    '''
cursor.execute(sales_per_day_sql)
actual_sales_per_day = cursor.fetchall()

# Convert SQL query result to DataFrame
actual_sales_df = pd.DataFrame(actual_sales_per_day, columns=['InvoiceDate', 'Total_Actual_Sales'])
actual_sales_df['InvoiceDate'] = pd.to_datetime(actual_sales_df['InvoiceDate'])

# Read prediction csv
prediction_df = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
# Convert to valid data types
prediction_df['InvoiceDate'] = pd.to_datetime(prediction_df['InvoiceDate'])
# Group by InvoiceDate and sum all columns starting with 'Predicted_Sales'
columns_to_sum = [col for col in prediction_df.columns if col.startswith('Predicted_Sales')]
grouped_df = prediction_df.groupby('InvoiceDate')[columns_to_sum].sum().reset_index()

# Rename columns for clarity
grouped_df = grouped_df.rename(columns={col: f'Total_{col}' for col in columns_to_sum})

# Ensure both DataFrames are sorted by InvoiceDate
grouped_df = grouped_df.sort_values('InvoiceDate')
actual_sales_df = actual_sales_df.sort_values('InvoiceDate')

# Merge the DataFrames on InvoiceDate
# We'll use merge instead of concat to handle potential date mismatches
merged_df = pd.merge(
    actual_sales_df,
    grouped_df,
    on='InvoiceDate',
    how='outer'  # Use 'outer' if you want to keep all dates from both DataFrames
)

# Reorder columns to have InvoiceDate first, then Total_Actual_Sales, followed by Total_Predicted_Sales columns
columns_order = ['InvoiceDate', 'Total_Actual_Sales'] + [col for col in merged_df.columns if col.startswith('Total_Predicted_Sales')]
merged_df = merged_df[columns_order]
# Replace NaN values with None (null in JSON)
merged_df = merged_df.replace({np.nan: None})
# Convert to dictionary for JSON serialization
sales_data = merged_df.to_dict('records')

print(sales_data)

# Close connection
cursor.close()
mydb.close()
