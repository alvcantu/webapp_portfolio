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


def dash_self_service():

    # Connect to MySQL database
    mydb, cursor = get_db_connection()    

    # Datamart selector query
    data_mart_list = get_db_data_marts()

    # Set default selections if not provided
    default_datamart = data_mart_list[0] if data_mart_list else ''
    selected_datamart = request.form.get('selected_datamart', default_datamart)

    # Gathers db description for selected data mart
    db_description_data_mart = get_db_description(selected_datamart) 
    columns_with_types = {
        column_name: data_type.decode() if isinstance(data_type, bytes) else str(data_type)
        for table in db_description_data_mart.values() for column_name, data_type, *_ in table
    }

    classified_columns = {
        column_name: {
            'name': column_name,
            'type': data_type,
            'classification': (
                "dimension" if any(data_type.startswith(t) for t in ('varchar', 'char', 'text', 'date')) else
                "measure" if any(data_type.startswith(t) for t in ('int', 'float')) else
                "other"
            )
        }
        for column_name, data_type in columns_with_types.items()
    }

    dimension_columns = [column for column, details in classified_columns.items() if details['classification'] == 'dimension']
    measure_columns = [column for column, details in classified_columns.items() if details['classification'] == 'measure']

    # Set default dimensions and measures
    default_dimension = dimension_columns[:1]  # Selecting the first dimension as default
    default_measure = measure_columns[:1]  # Selecting the first measure as default

    selected_dimensions = request.form.getlist('selected_dimensions') or default_dimension
    selected_measures = request.form.getlist('selected_measures') or default_measure

    # Default visualization type
    selected_visual = request.form.get('selected_visual', 'Table')

    prompt = f"""
    Given the following database schema with column comments for context:
    {db_description_data_mart}

    Generate a query that sums these measures:
    {selected_measures}
    And groups them by these dimensions:
    {selected_dimensions}
    """

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    }
    data = {
        "model": "openrouter/auto",
        "messages": [
            {"role": "system", "content": "You are a MySQL server query generator that outputs code ready to be executed."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    sql_query_unclean = response.json()['choices'][0]['message']['content']
    sql_query = extract_sql_query(sql_query_unclean)

    cursor.execute(sql_query)
    data_output = cursor.fetchall()

    if selected_visual == 'Table':
        data_output_html = get_table_html(sql_query)
    else:
        chart_data = {
            'labels': [row[0] for row in data_output],  # Assuming the first column is for labels
            'datasets': [
                {
                    'label': measure,
                    'data': [row[i] for row in data_output],  # Index according to measure column position
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',  # Example color
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'borderWidth': 1,
                    'fill': True if selected_visual == 'Area' else False
                } for i, measure in enumerate(selected_measures, start=1)
            ]
        }
        data_output_html = chart_data

    return render_template('dash_self_service.html',
                           data_mart_list=data_mart_list,
                           dimension_columns=dimension_columns,
                           measure_columns=measure_columns,
                           selected_datamart=selected_datamart,
                           selected_dimensions=selected_dimensions,
                           selected_measures=selected_measures,
                           selected_visual=selected_visual,
                           data_output=data_output_html)


print(data_marts)
print(columns_with_types)

