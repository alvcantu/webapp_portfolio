import pandas as pd
import numpy as np
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

# Convert df for MySQL
def convert_df_for_mysql(df):
    # Convert object types that should be ENUM to categorical with a specified set of categories
    categories = {
        'job': ['admin.', 'blue-collar', 'entrepreneur', 'housemaid', 'management', 'retired', 'self-employed', 'services', 'student', 'technician', 'unemployed', 'unknown'],
        'marital': ['divorced', 'married', 'single', 'unknown'],
        'default': ['no', 'yes', 'unknown'],
        'housing': ['no', 'yes', 'unknown'],
        'loan': ['no', 'yes', 'unknown'],
        'contact': ['cellular', 'telephone', 'unknown'],
        'month': ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'],
        'poutcome': ['failure', 'nonexistent', 'success', 'unknown'],
        'y': ['yes', 'no']
    }

    for col, cats in categories.items():
        df[col] = pd.Categorical(df[col], categories=cats, ordered=False)

    # Ensure 'balance' is float32 for MySQL FLOAT compatibility
    df['balance'] = df['balance'].astype('float32')

    # Convert duration, campaign, pdays, previous to int32 for MySQL INT compatibility
    for col in ['duration', 'campaign', 'pdays', 'previous']:
        df[col] = df[col].astype('int32')

    # Convert 'y' to 'subscribed_y' with boolean interpretation
    df['subscribed_y'] = df['y'].map({'yes': 1, 'no': 0}).astype('int8')  # TINYINT in MySQL
    del df['y']  # Remove the old 'y' column

    # Rename default to default_credit
    df = df.rename(columns={'default': 'default_credit'})

    # Add customer_id as a unique identifier
    df['customer_id'] = range(1, len(df) + 1)
    
    # Ensure all numeric columns are numeric to catch any potential issues
    numeric_columns = ['age', 'balance', 'duration', 'campaign', 'pdays', 'previous']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')  # Coerce to handle potential non-numeric values

    return df

# Function to insert prepared DataFrame into MySQL
def insert_dataframe_into_mysql(df_ready, cursor, mydb):
    # Prepare the insert statement based on the table structure
    # Assuming the table already exists due to the previous CREATE TABLE query
    cols = ', '.join(df_ready.columns.tolist())
    placeholders = ', '.join(['%s'] * len(df_ready.columns))

    insert_query = f"""INSERT INTO BM_FactCustomers ({cols}) VALUES ({placeholders})"""

    # Convert DataFrame to list of tuples
    data_to_insert = list(df_ready.itertuples(index=False, name=None))
    
    try:
        # Execute the SQL command
        cursor.executemany(insert_query, data_to_insert)
        # Commit your changes in the database
        mydb.commit()
        print(f"{cursor.rowcount} records inserted.")
    except Error as e:
        print(f"Error: {e}")
        mydb.rollback()  # Rollback in case there is any error
    
    finally:
        if (mydb.is_connected()):
            cursor.close()
            mydb.close()
            print("MySQL connection is closed")

# Read data from CSV files
df_nonadditional = pd.read_csv('/home/alvcantu/bank_marketing/bank-full.csv',sep=';')
df_additional = pd.read_csv('/home/alvcantu/bank_marketing/bank-additional-full.csv', sep=';')

# Drop columns that are not needed in df additional as they're only available in one csv
df_nonadditional = df_nonadditional.drop(['day'], axis=1)
df_additional = df_additional.drop(['day_of_week', 'emp.var.rate', 'cons.price.idx', 'cons.conf.idx', 'euribor3m', 'nr.employed'], axis=1)

# Union the two dataframes
union_df = pd.concat([df_nonadditional, df_additional], ignore_index=True)

# Remove duplicates on merged dataframe
df = union_df.drop_duplicates()

# Replace Nan Balance with 0
df['balance'] = df['balance'].fillna(0)
# Replace 'other' with 'unknown for poutomc column
df['poutcome'] = df['poutcome'].replace('other', 'unknown')

# Assuming you have your DataFrame named 'df'
df_ready = convert_df_for_mysql(df)
column_order = [
    'customer_id', 'age', 'job', 'marital', 'education', 'default_credit', 'balance', 'housing', 'loan', 'contact', 'month', 
    'duration', 'campaign', 'pdays', 'previous', 'poutcome', 'subscribed_y'
]
df_ready = df_ready[column_order]

# SQL query for dropping table
sql_drop_table = """
DROP TABLE BM_FactCustomers;
"""

# SQL query for creating table
sql_create_table = """
CREATE TABLE BM_FactCustomers (
    customer_id INT PRIMARY KEY COMMENT 'Customer identification',
    age INT COMMENT 'Age in years',
    job ENUM('admin.', 'blue-collar', 'entrepreneur', 'housemaid', 'management', 'retired', 'self-employed', 'services', 'student', 'technician', 'unemployed', 'unknown') COMMENT 'Type of job',
    marital ENUM('divorced', 'married', 'single', 'unknown') COMMENT 'Marital status',
    education VARCHAR(300) COMMENT 'Education level',
    default_credit ENUM('no', 'yes', 'unknown') COMMENT 'Does customer have credit in default?',
    balance FLOAT COMMENT 'Balance amount in Euros',
    housing ENUM('no', 'yes', 'unknown') COMMENT 'Does customer have housing loan?',
    loan ENUM('no', 'yes', 'unknown') COMMENT 'Does customer have personal loan?',
    contact ENUM('cellular', 'telephone', 'unknown') COMMENT 'Contact communication type',
    month ENUM('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec') COMMENT 'Last contact month of year',
    duration FLOAT COMMENT 'last contact duration, in seconds',
    campaign INT COMMENT 'Number of contacts performed during this campaign and for this client',
    pdays FLOAT COMMENT 'Number of days that passed by after the client was last contacted from a previous campaign',
    previous INT COMMENT 'Number of contacts performed before this campaign and for this client',
    poutcome ENUM('failure', 'nonexistent', 'success', 'unknown') COMMENT 'Outcome of the previous marketing campaign',
    subscribed_y TINYINT(1) COMMENT 'Has the client subscribed a term deposit?',
    CONSTRAINT unique_customer_id UNIQUE (customer_id)
);
"""

# MySQL connection
mydb, cursor = get_db_connection()

# Execute SQL drop table query if needed
cursor.execute(sql_drop_table)

# Execute SQL create query
cursor.execute(sql_create_table)

# Call the function to insert data
insert_dataframe_into_mysql(df_ready, cursor, mydb)

