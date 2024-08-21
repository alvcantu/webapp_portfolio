import pandas as pd
import numpy as np
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns

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
    df['StockCode'] = df['StockCode'].astype(str)  # Corrected typo
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0).astype(int)  # Assuming 0 for NaN, adjust as needed
    df['UnitPrice'] = pd.to_numeric(df['UnitPrice'], errors='coerce').fillna(0).round(2)  # Assuming 0 for NaN, rounded to 2 decimal places
    df['CustomerID'] = pd.to_numeric(df['CustomerID'], errors='coerce').fillna(-1).astype(int)  # Assuming -1 for NaN, adjust as needed
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
    else:
        print("All invoices are valid.")

    return invalid_invoices

def create_tables(cursor):
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
        FOREIGN KEY (InvoiceID) REFERENCES ONR_DimInvoice(InvoiceID)
    ) COMMENT='Fact table for transactions';
    """
    cursor.execute(create_fact_transactions)


def normalize_and_insert_data(df):
    # Validate the invoices
    answ = validate_invoices(df)

    # Proceed only if all invoices are valid
    if answ != 'All invoices are valid.':
        print("Invoices are not valid. Data insertion aborted.")
        return

    mydb, cursor = get_db_connection()

    try:
        # Create tables if they don't exist
        create_tables(cursor)
        mydb.commit()

        # Normalize data
        dim_invoice = df[['InvoiceNo', 'CustomerID', 'Country', 'InvoiceDate']].drop_duplicates()
        fact_transactions = df.drop(['CustomerID', 'Country', 'InvoiceDate'], axis=1)

        # Insert into ONR_DimInvoice
        for _, row in dim_invoice.iterrows():
            cursor.execute("""
            INSERT INTO ONR_DimInvoice (InvoiceID, CustomerID, Country, InvoiceDate)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE CustomerID=VALUES(CustomerID), Country=VALUES(Country), InvoiceDate=VALUES(InvoiceDate)
            """, (row['InvoiceNo'], row['CustomerID'], row['Country'], row['InvoiceDate']))

        # Insert into ONR_FactTransactions
        for _, row in fact_transactions.iterrows():
            cursor.execute("""
            INSERT INTO ONR_FactTransactions (InvoiceID, StockCode, Description, Quantity, UnitPrice)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE StockCode=VALUES(StockCode), Description=VALUES(Description), Quantity=VALUES(Quantity), UnitPrice=VALUES(UnitPrice)
            """, (row['InvoiceNo'], row['StockCode'], row['Description'], row['Quantity'], row['UnitPrice']))

        mydb.commit()
        print("Data has been successfully inserted into the database.")

    except Error as e:
        print(f"Error: {e}")
    finally:
        if mydb.is_connected():
            cursor.close()
            mydb.close()


# Convert data types
df = check_data_types(df)

# Normalize and insert data into mySQL
normalize_and_insert_data(df)

