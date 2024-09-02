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
print(df.head())