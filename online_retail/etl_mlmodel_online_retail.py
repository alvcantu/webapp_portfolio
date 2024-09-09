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
df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')
# Feature Engineering
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['Day'] = df['InvoiceDate'].dt.day
df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')

# Encode categorical variables
le = LabelEncoder()
df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
df['Country'] = le.fit_transform(df['Country'])

# Features the model was trained on
features = ['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt1_xgboost_salesmodel_online_retail.json')

# Make predictions
# Only using features in the training set
X = df[features]
predictions = model.predict(X)

# Adding column with predictes sales to the original dataframe
df['Predicted_Sales1'] = predictions

# Converting Predicted_Sales1 to float and rounding to two decimal places
df['Predicted_Sales1'] = df['Predicted_Sales1'].astype(float)
df['Predicted_Sales1'] = df['Predicted_Sales1'].round(2)

# Filtering df so it has only InvoiceID and Predicted_Sales1 columns
df_to_insert = df[['TransactionID', 'Predicted_Sales1']]

print(df_to_insert.head())

# SQL to delete the column if it exists
delete_column_sql = """
ALTER TABLE ONR_FactTransactions 
DROP COLUMN Predicted_Sales1;
"""

# SQL to add the column if it doesn't exist
add_column_sql = """
ALTER TABLE ONR_FactTransactions 
ADD COLUMN Predicted_Sales1 FLOAT;
"""

# SQL to update the comment for the new column
update_comment_sql = """
ALTER TABLE ONR_FactTransactions 
MODIFY COLUMN Predicted_Sales1 FLOAT COMMENT 'Predicted sales (UnitPrice * Quantity) with first machine learning model using XGBoost and RandomizedSearchCV.';
"""

# Adding new predicted sales column to ONR_FactTransactions table in mysql
try:
    mydb, cursor = get_db_connection()
    cursor.execute(delete_column_sql)
    cursor.execute(add_column_sql)
    cursor.execute(update_comment_sql)
    mydb.commit()  # Commit the transaction for schema changes

    # Function to update data in MySQL
    def update_mysql(row):
        check_exists_sql = "SELECT 1 FROM ONR_FactTransactions WHERE TransactionID = %s"
        cursor.execute(check_exists_sql, (row['TransactionID'],))
        if cursor.fetchone():
            update_sql = """
            UPDATE ONR_FactTransactions 
            SET Predicted_Sales1 = %s
            WHERE InvoiceID = %s
            """
            cursor.execute(update_sql, (row['Predicted_Sales1'], row['TransactionID']))
        else:
            print(f"Warning: TransactionID {row['TransactionID']} does not exist in the database.")

    # Define chunk size
    chunk_size = 100  # Adjust this number based on your preference or system capabilities

    # Total number of rows
    total_rows = len(df_to_insert)
    
    # Loop through the dataframe in chunks
    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        chunk = df_to_insert.iloc[start:end]
        
        # Apply the update function to this chunk
        chunk.apply(update_mysql, axis=1)
        
        # Commit after each chunk
        mydb.commit()
        
        # Print progress
        print(f"Processed {end} of {total_rows} records.")

    print("Database update complete.")

except Error as error:
    print(f"Failed to update database: {error}")
    mydb.rollback()  # Rollback in case of error

finally:
    # Close the connection
    if mydb.is_connected():
        cursor.close()
        mydb.close()
        print("MySQL connection is closed.")