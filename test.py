# test
import pandas as pd
import mysql.connector
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from datetime import datetime

def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor(dictionary=True)  # This is the key change
    return mydb, cursor


# Connect to MySQL database
mydb, cursor = get_db_connection()

# SQL query that returns all column names for all models
column_names_sql = '''
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'ONR_FactTransactions'
    AND column_name LIKE 'Predicted_Sales%';
    '''
# Fetch column names
cursor.execute(column_names_sql)
column_names = [row['COLUMN_NAME'] for row in cursor.fetchall()]

# Function to execute queries
def execute_and_fetch(sql, cursor):
    cursor.execute(sql)
    return cursor.fetchall()

# Function to generate SQL for each metric
def generate_sql(metric, column_names):
    sql_parts = []
    for col in column_names:
        sql_parts.append(f'''
            SELECT '{col}' AS prediction_type, {dynamic_sqls[metric].format(col=col)} AS {metric}
            FROM ONR_FactTransactions
        ''')
    # Ensure there's at least one part
    if not sql_parts:
        return ""
    # Join with UNION ALL between all parts except the last one
    return ' UNION ALL '.join(sql_parts) + ';'

# Define metrics
metrics = ['RMSE', 'MSE', 'MAE', 'MAPE']
dynamic_sqls = {
    'RMSE': 'SQRT(AVG(POWER((Quantity * UnitPrice) - {col}, 2)))',
    'MSE': 'SUM(POW((UnitPrice * Quantity) - {col}, 2)) / COUNT(*)',
    'MAE': 'AVG(ABS((UnitPrice * Quantity) - {col}))',
    'MAPE': '(SUM(ABS((Quantity * UnitPrice) - Predicted_Sales1) / NULLIF(Quantity * UnitPrice, 0)) / COUNT(*)) * 100'
}

# Execute queries and combine results
data_output = []
for metric in metrics:
    sql = generate_sql(metric, column_names)
    if sql:  # Only attempt to execute if SQL was generated
        results = execute_and_fetch(sql, cursor)
        data_output.extend(results)

# Close connection
cursor.close()
mydb.close()

print(data_output)
