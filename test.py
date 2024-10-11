import csv
import requests
import json
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
import os
from datetime import datetime
from decimal import Decimal

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

# Prepare data for Chart.js (NEEDS FULL REWRITE)
def prepare_data_for_chart(sql_query):
    # Connect to MySQL database
    mydb, cursor = get_db_connection()

    # Execute the query
    cursor.execute(sql_query)
    data_output = cursor.fetchall()

    # Get headers from cursor description
    headers = [desc[0] for desc in cursor.description]

    # Close database connection
    cursor.close()
    mydb.close()

    # Determine the number of columns in the data
    num_columns = len(headers)

    # Helper function to determine if a value is a number
    def is_numeric(value):
        return isinstance(value, (int, float, Decimal))

    # Helper function to determine if a value is a date
    def is_date(value):
        try:
            if isinstance(value, datetime):
                return True
            datetime.strptime(str(value), '%Y-%m-%d')
            return True
        except (ValueError, TypeError):
            return False

    # Helper function to format date values
    def format_date(value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        return str(value)

    # Split headers into dimensions and measures
    dimensions = []
    measures = []

    for idx, header in enumerate(headers):
        # Check if the first data row's value is numeric or a date
        if is_numeric(data_output[0][idx]):
            measures.append(header)
        else:
            dimensions.append(header)

    # Handling different cases based on the number of dimensions and measures
    if len(dimensions) == 1 and len(measures) == 1:
        # Case 1: Single Dimension with One Measure
        labels = [format_date(row[0]) if is_date(row[0]) else str(row[0]) for row in data_output]
        data = [float(row[1]) for row in data_output]

        return {
            "labels": labels,
            "datasets": [{
                "label": measures[0],
                "data": data,
                "backgroundColor": 'rgba(54, 162, 235, 0.2)',
                "borderColor": 'rgba(54, 162, 235, 1)',
                "borderWidth": 1
            }],
            "xAxisLabels": dimensions,
            "yAxisLabels": measures
        }

    elif len(dimensions) > 1 and len(measures) == 1:
        # Case 2: Multiple Dimensions with One Measure
        labels = [format_date(row[0]) if is_date(row[0]) else str(row[0]) for row in data_output]
        data = [float(row[1]) for row in data_output]

        return {
            "labels": labels,
            "datasets": [{
                "label": measures[0],
                "data": data,
                "backgroundColor": 'rgba(255, 206, 86, 0.2)',
                "borderColor": 'rgba(255, 206, 86, 1)',
                "borderWidth": 1
            }],
            "xAxisLabels": dimensions,
            "yAxisLabels": measures
        }

    elif len(dimensions) == 1 and len(measures) > 1:
        # Case 3: Single Dimension with Multiple Measures
        labels = [format_date(row[0]) if is_date(row[0]) else str(row[0]) for row in data_output]
        datasets = []

        for i, measure in enumerate(measures):
            data = [float(row[i + 1]) for row in data_output]
            datasets.append({
                "label": measure,
                "data": data,
                "backgroundColor": f'rgba({54 + i * 30}, {162 - i * 30}, 235, 0.2)',
                "borderColor": f'rgba({54 + i * 30}, {162 - i * 30}, 235, 1)',
                "borderWidth": 1
            })

        return {
            "labels": labels,
            "datasets": datasets,
            "xAxisLabels": dimensions,
            "yAxisLabels": measures
        }

    elif len(dimensions) > 1 and len(measures) > 1:
        # Case 4: Multiple Dimensions with Multiple Measures
        labels = [format_date(row[0]) if is_date(row[0]) else str(row[0]) for row in data_output]
        datasets = []

        for i, measure in enumerate(measures):
            data = [float(row[i + len(dimensions)]) for row in data_output]
            datasets.append({
                "label": measure,
                "data": data,
                "backgroundColor": f'rgba({75 + i * 30}, {192 - i * 30}, 192, 0.2)',
                "borderColor": f'rgba({75 + i * 30}, {192 - i * 30}, 192, 1)',
                "borderWidth": 1
            })

        return {
            "labels": labels,
            "datasets": datasets,
            "xAxisLabels": dimensions,
            "yAxisLabels": measures
        }

    else:
        return {"labels": [], "datasets": [], "xAxisLabels": [], "yAxisLabels": []}

sql_query = '''
SELECT 
    date, 
    close_price 
FROM 
    ST_FactPrices 
WHERE 
    ticker = 'TSLA' 
    AND date >= CURDATE() - INTERVAL 3 WEEK LIMIT 6900;
'''

print(prepare_data_for_chart(sql_query))