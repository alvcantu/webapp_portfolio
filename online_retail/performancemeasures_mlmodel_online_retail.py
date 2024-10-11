import csv
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

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
with open('online_retail/performancemeasures_mlmodel_online_retail.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(performance_data)

# Close database connection
cursor.close()
mydb.close()