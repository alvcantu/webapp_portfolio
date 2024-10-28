import pandas as pd
import numpy as np
import json
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
import mysql.connector
from mysql.connector import Error

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

# Extract data from MySQL
mydb, cursor = get_db_connection()
cursor.execute("SELECT * FROM BM_FactCustomers;")
data = cursor.fetchall()
columns = [i[0] for i in cursor.description]  # Get column names
df = pd.DataFrame(data, columns=columns)

# Copy of original dataframe
df_encoded = df.copy()

# Identify categorical columns
categorical_columns = df.select_dtypes(include=['object']).columns
# Dictionary to hold the label encoders for each column
encoders = {}
for column in categorical_columns:
    # Initialize LabelEncoder for each categorical column
    le = LabelEncoder()
    # Fit and transform the column, then assign back to the new DataFrame
    df_encoded[column] = le.fit_transform(df[column])
    # Save the classes for potential inverse transform later
    encoders[column] = le.classes_


# Load model
model = xgb.Booster()
model.load_model('bank_marketing/ml_model_bank_marketing.json')

df_encoded_dropped = df_encoded.drop(columns=['customer_id', 'duration','subscribed_y'])

# Convert to DMatrix
X = xgb.DMatrix(df_encoded_dropped)
predictions = model.predict(X)

# Add predictions to original dataframe
df['predicted_subscribed_y'] = predictions
# Convert to float
df['predicted_subscribed_y'] = df['predicted_subscribed_y'].astype(float)
# Round to two decimal places
df['predicted_subscribed_y'] = df['predicted_subscribed_y'].round(2)

# Creating dataframe to insert into MySQL
df_to_insert = df[['customer_id', 'predicted_subscribed_y']]

# SQL to create new column for predicted subscribed_y
sql_create_column = """
ALTER TABLE BM_FactCustomers
ADD COLUMN predicted_subscribed_y DECIMAL(3,2) COMMENT 'Predicted probability of customer subscribing with first machine learning model using XGBoost and Bayesian Optimization.';
"""

# Execute the SQL statement
cursor.execute(sql_create_column)
mydb.commit()  # Commit the transaction for schema changes

# SQL to insert the new column into the table
sql_insert_column = """
INSERT INTO BM_FactCustomers (customer_id, predicted_subscribed_y)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE predicted_subscribed_y = VALUES(predicted_subscribed_y);
"""

# Convert DataFrame to a list of tuples for executemany
data_to_insert = list(zip(df_to_insert['customer_id'], df_to_insert['predicted_subscribed_y']))

try:
    # Execute the query with many parameters
    cursor.executemany(sql_insert_column, data_to_insert)

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


