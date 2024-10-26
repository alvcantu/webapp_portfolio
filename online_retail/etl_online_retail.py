import pandas as pd
import numpy as np
import mysql.connector
from datetime import timedelta

# Load data into a DataFrame
df = pd.read_csv('/home/alvcantu/online_retail/online_retail.csv')

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

# Clean and convert data types
def check_data_types(df):
    df['InvoiceNo'] = df['InvoiceNo'].astype(str)
    df['StockCode'] = df['StockCode'].astype(str)

    # Convert to datetime mySQL understands
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate']).dt.strftime('%Y-%m-%d')

    # Convert to native Python int and float
    df['Quantity'] = df['Quantity'].fillna(0).astype('int32').tolist()  # Convert to list to get Python int
    df['UnitPrice'] = df['UnitPrice'].fillna(0).round(2).astype('float32').tolist()  # Convert to list for Python float


    df['CustomerID'] = df['CustomerID'].astype(str)
    df['Country'] = df['Country'].astype(str)

    return df


# Check if there are invoices that make no sense.
def validate_invoices(df):
    invalid_invoices = []

    # Group by InvoiceNo
    grouped = df.groupby('InvoiceNo')

    for invoice_no, group in grouped:
        # Check if all Country values are the same
        if group['Country'].nunique() > 1:
            invalid_invoices.append(invoice_no)
            continue  # Skip to the next group since this one is already invalid

        # Check if all CustomerID values are the same
        if group['CustomerID'].nunique() > 1:
            invalid_invoices.append(invoice_no)
            continue  # Skip to the next group since this one is already invalid

        # Check if all InvoiceDate values are within 5 minutes of each other
        time_diff = group['InvoiceDate'].max() - group['InvoiceDate'].min()
        if time_diff > pd.Timedelta(minutes=2):
            invalid_invoices.append(invoice_no)

    if invalid_invoices:
        print(f"Invalid Invoices: {invalid_invoices}")
        return False
    else:
        print("All invoices are valid.")
        return True


# Function to create tables in mySQL database
def create_tables(cursor):
    # Delete ONR_FactTransactions if exists
    drop_fact_transactions = '''
    DROP TABLE IF EXISTS ONR_FactTransactions;
    '''
    cursor.execute(drop_fact_transactions)

    # Delete ONR_DimInvoice if exists
    drop_dim_invoice = '''
    DROP TABLE IF EXISTS ONR_DimInvoice;
    '''
    cursor.execute(drop_dim_invoice)

    # Create ONR_DimInvoice table
    create_dim_invoice = """
    CREATE TABLE IF NOT EXISTS ONR_DimInvoice (
        InvoiceID VARCHAR(255) PRIMARY KEY COMMENT 'Unique identifier for each invoice',
        CustomerID VARCHAR(255) COMMENT 'ID of the customer',
        Country VARCHAR(255) COMMENT 'Country of the customer',
        InvoiceDate DATETIME COMMENT 'Date of the invoice'
    ) COMMENT='Dimension table for invoices';
    """
    cursor.execute(create_dim_invoice)

    # Create ONR_FactTransactions table
    create_fact_transactions = """
    CREATE TABLE IF NOT EXISTS ONR_FactTransactions (
        InvoiceID VARCHAR(255) COMMENT 'Foreign key to ONR_DimInvoice',
        StockCode VARCHAR(255) COMMENT 'Stock code of the product',
        Description TEXT COMMENT 'Description of the product',
        Quantity INT COMMENT 'Quantity of the product',
        UnitPrice DECIMAL(10, 2) COMMENT 'Unit price of the product',
        Total_Actual_Sales DECIMAL(10, 2) COMMENT 'Total sales amount calculated as Quantity multiplied by Unit Price',
        FOREIGN KEY (InvoiceID) REFERENCES ONR_DimInvoice(InvoiceID)
    ) COMMENT='Fact table for transactions';
    """
    cursor.execute(create_fact_transactions)

# Normalize data (split into two tables) and insert it into mySQL tables after creating them
def normalize_and_insert_data(df):
    mydb, cursor = get_db_connection()

    # Create tables if they don't exist
    create_tables(cursor)

    # Normalize data
    dim_invoice = df[['InvoiceNo', 'CustomerID', 'Country', 'InvoiceDate']].drop_duplicates()
    fact_transactions = df[['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'UnitPrice']]

    # Fill NaN values with appropriate defaults
    fact_transactions = fact_transactions.fillna({'Description': '', 'Quantity': 0, 'UnitPrice': 0.0})

    # Prepare SQL for insert/update
    insert_dim_invoice = """
    INSERT INTO ONR_DimInvoice (InvoiceID, CustomerID, Country, InvoiceDate)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE CustomerID=VALUES(CustomerID), Country=VALUES(Country), InvoiceDate=VALUES(InvoiceDate)
    """

    insert_fact_transactions = """
    INSERT INTO ONR_FactTransactions (InvoiceID, StockCode, Description, Quantity, UnitPrice)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE StockCode=VALUES(StockCode), Description=VALUES(Description),
    Quantity=VALUES(Quantity), UnitPrice=VALUES(UnitPrice)
    """

    # Define chunk size
    chunk_size = 1000  # Adjust this based on your needs and the size of your data

    # Insert data in chunks for dim_invoice
    for start in range(0, len(dim_invoice), chunk_size):
        end = start + chunk_size
        dim_invoice_chunk = dim_invoice.iloc[start:end]
        dim_invoice_data = [tuple(row) for row in dim_invoice_chunk.to_records(index=False)]
        cursor.executemany(insert_dim_invoice, dim_invoice_data)
        mydb.commit()  # Commit after each chunk

    # Insert data in chunks for fact_transactions
    for start in range(0, len(fact_transactions), chunk_size):
        end = start + chunk_size
        fact_transactions_chunk = fact_transactions.iloc[start:end]
        fact_transactions_data = [
            tuple([item if not isinstance(item, (np.int64, np.float64)) else item.item() for item in row])
            for row in fact_transactions_chunk.to_records(index=False)
        ]
        cursor.executemany(insert_fact_transactions, fact_transactions_data)
        mydb.commit()  # Commit after each chunk

    print("Data has been successfully inserted into the database in chunks.")

    # Update Total_Actual_Sales column in ONR_FactTransactions
    total_sales_sql = '''
    UPDATE ONR_FactTransactions
    SET Total_Actual_Sales = ROUND(Quantity * UnitPrice, 2);
    '''
    # Execute the SQL query
    cursor.execute(total_sales_sql)
    mydb.commit()

    cursor.close()
    mydb.close()


# Change to datetime so invoice can be validated
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

# Normalize and insert data into mySQL
if validate_invoices(df):
    # Convert data types
    df = check_data_types(df)
    normalize_and_insert_data(df)
else:
    print("Data insertion aborted due to invalid invoices.")

