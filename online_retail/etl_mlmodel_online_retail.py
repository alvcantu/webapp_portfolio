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

print(df.head())

# Convert to valid data types
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

# Feature Engineering
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['Day'] = df['InvoiceDate'].dt.day
df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
df['IsWeekend'] = df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
df['Quarter'] = df['InvoiceDate'].dt.quarter
df['Season'] = df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else 
                                         'Spring' if x in [3, 4, 5] else 
                                         'Summer' if x in [6, 7, 8] else 'Autumn')

# Encode categorical variables
le = LabelEncoder()
df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
df['Country'] = le.fit_transform(df['Country'])
df['Season'] = le.fit_transform(df['Season'])

# Features the model was trained on
features = ['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'Country']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt2_xgboost_mlmodel_online_retail.json')

# Make predictions
# Only using features in the training set
X = df[features]
predictions = model.predict(X)

# Adding column with predictes sales to the original dataframe
df['Predicted_Sales2'] = predictions

# Converting Predicted_Sales1 to float and rounding to two decimal places
df['Predicted_Sales2'] = df['Predicted_Sales2'].astype(float)
df['Predicted_Sales2'] = df['Predicted_Sales2'].round(2)

# Filtering df so it has only InvoiceID and Predicted_Sales1 columns
df_to_insert = df[['TransactionID', 'Predicted_Sales2']]

print(df_to_insert.head())

# SQL to delete the column if it exists
delete_column_sql = """
ALTER TABLE ONR_FactTransactions 
DROP COLUMN Predicted_Sales2;
"""

# SQL to add the column if it doesn't exist
add_column_sql = """
ALTER TABLE ONR_FactTransactions 
ADD COLUMN Predicted_Sales2 FLOAT;
"""

# SQL to update the comment for the new column
update_comment_sql = """
ALTER TABLE ONR_FactTransactions 
MODIFY COLUMN Predicted_Sales2 FLOAT COMMENT 'Predicted sales (UnitPrice * Quantity) with second machine learning model using XGBoost and Bayesian Optimization.';
"""

# Adding new predicted sales column to ONR_FactTransactions table in mysql
mydb, cursor = get_db_connection()
#cursor.execute(delete_column_sql)
cursor.execute(add_column_sql)
cursor.execute(update_comment_sql)
mydb.commit()  # Commit the transaction for schema changes

# SQL to insert the new column into the table
try:
    # Your SQL statement
    update_sql = """
    INSERT INTO ONR_FactTransactions (TransactionID, Predicted_Sales2)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE Predicted_Sales2 = VALUES(Predicted_Sales2);
    """

    # Convert DataFrame to a list of tuples for executemany
    data_to_insert = list(zip(df_to_insert['TransactionID'], df_to_insert['Predicted_Sales2']))

    # Execute the query with many parameters
    cursor.executemany(update_sql, data_to_insert)

    # Commit the transaction
    mydb.commit()

    print(f"{cursor.rowcount} records were successfully inserted or updated.")

except Error as error:
    print(f"Failed to insert data into MySQL table {error}")
    mydb.rollback()  # Rollback in case of error

finally:
    # Closing the connection
    if mydb.is_connected():
        cursor.close()
        mydb.close()
        print("MySQL connection is closed")