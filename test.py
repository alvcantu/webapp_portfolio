from flask import Flask, request, render_template, url_for
from youtube_transcript_api import YouTubeTranscriptApi
import re
import requests
import json
import mysql.connector
import pandas as pd
import os
from graphviz import Digraph
import sqlparse
from datetime import datetime

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

# Extracts all data marts
def get_db_data_marts():
    # Connect to MySQL database
    mydb, cursor = get_db_connection()

    # Get list of all tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    # Extract codes from table names
    codes = set()
    for table in tables:
        # Assuming each table name is a tuple with one element
        table_name = table[0]
        # Split the table name at the underscore and take the first part
        if '_' in table_name:
            code = table_name.split('_')[0]
            codes.add(code)
    
    return list(codes)

# Extracts information schema of each table in mySQL database
def get_db_description(data_mart=None):
    # Connect to MySQL database
    mydb, cursor = get_db_connection()

    # Get list of all tables or filtered tables based on data_mart
    if data_mart:
        # Filter tables that start with the data_mart code followed by an underscore
        cursor.execute(f"SHOW TABLES LIKE '{data_mart}_%'")
    else:
        cursor.execute("SHOW TABLES")
    
    tables = cursor.fetchall()

    # Dictionary to hold descriptions of all tables
    db_description = {}

    # Loop through each table and get its description
    for (table_name,) in tables:
        # Query to get the schema information for the current table
        query = f"""
        SELECT COLUMN_NAME AS 'Field', COLUMN_TYPE AS 'Type', IS_NULLABLE AS 'Null', 
                COLUMN_KEY AS 'Key', COLUMN_COMMENT AS 'Comment'
        FROM information_schema.COLUMNS 
        WHERE TABLE_NAME ='{table_name}'
        """
        cursor.execute(query)
        table_description = cursor.fetchall()
        db_description[table_name] = table_description

    return db_description

data_marts = get_db_data_marts()

db_description_data_mart = get_db_description('SP') 
# Variable that holds all columns and their data type from db description
columns_with_types = {
    column_name: data_type.decode() if isinstance(data_type, bytes) else str(data_type)
    for table in db_description_data_mart.values()    for column_name, data_type, *_ in table  # Using _ to ignore other elements in the tuple
}
# Expands ov dictionary above and adds classification according to data type for further use
classified_columns = {
    column_name: {
        'type': data_type,
        'classification': (
            "dimension" if data_type.startswith(('varchar', 'char', 'text', 'date')) else
            "measure" if data_type.startswith(('int', 'float')) else
            "other"
        )
    }
    for column_name, data_type in columns_with_types.items()
}


print(data_marts)
print(columns_with_types)

