from flask import Flask, request, render_template, url_for, jsonify
import re
import csv
import requests
import json
import mysql.connector
from mysql.connector import Error
from html import escape
import pandas as pd
import os
from graphviz import Digraph
import sqlparse
from datetime import datetime
from decimal import Decimal


# Initializes Flask app, backend framework that connects to front-end and computes all logic
app = Flask(__name__, static_url_path='/static')

# Open Router API key used to connect to different LLM's
OPENROUTER_API_KEY = "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"

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

# Check if the query is read-only
def is_read_only_query(sql_query):
    # Parse the SQL query
    parsed = sqlparse.parse(sql_query)[0]

    # Check if the query is read-only
    if parsed.get_type().upper() not in ['SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN']:
        return False, "Error: Only read-only queries are allowed to avoid modifying the dataset."
    
    return True, None

# Prepare data for Chart.js
def prepare_data_for_chart(data_output):
    if not data_output:
        return {"labels": [], "datasets": [], "xAxisLabels": [], "yAxisLabels": []}

    # Assuming the first row contains column names or labels
    headers = [str(header) for header in data_output[0]]
    data_output = data_output[1:]  # Remove headers from data

    # Determine the number of columns in the data
    num_columns = len(headers)
    
    # Extract axis labels from headers
    xAxisLabels = headers[0] if num_columns > 0 else "X-Axis"
    yAxisLabels = headers[1] if num_columns > 1 else "Y-Axis"

    # Case 1: Single Dimension with One Measure
    if num_columns == 2:
        labels = [str(row[0]) for row in data_output]
        data = [float(row[1]) if isinstance(row[1], Decimal) else row[1] for row in data_output]

        return {
            "labels": labels,
            "datasets": [{
                "label": yAxisLabels,
                "data": data,
                "backgroundColor": 'rgba(54, 162, 235, 0.2)',
                "borderColor": 'rgba(54, 162, 235, 1)',
                "borderWidth": 1
            }],
            "xAxisLabels": [xAxisLabels],
            "yAxisLabels": [yAxisLabels]
        }

    # Case 2: Single Dimension with Multiple Measures
    elif num_columns > 2:
        labels = [str(row[0]) for row in data_output]
        datasets = []
        for i in range(1, num_columns):
            data = [float(row[i]) if isinstance(row[i], Decimal) else row[i] for row in data_output]
            datasets.append({
                "label": headers[i],
                "data": data,
                "backgroundColor": f'rgba({54 + i*20}, {162 - i*20}, {235 - i*10}, 0.2)',
                "borderColor": f'rgba({54 + i*20}, {162 - i*20}, {235 - i*10}, 1)',
                "borderWidth": 1
            })

        return {
            "labels": labels,
            "datasets": datasets,
            "xAxisLabels": [xAxisLabels],
            "yAxisLabels": headers[1:]  # All measures labels for Y-axis
        }

    # Case 3 & 4: For simplicity, treating them similarly since handling would be complex without clear distinction
    else:
        # Here we'll assume the first two columns could be dimensions for labels
        dimensions = [f"{row[0]} - {row[1]}" if len(row) > 1 else str(row[0]) for row in data_output]
        data = [float(row[2]) if isinstance(row[2], Decimal) else row[2] for row in data_output if len(row) > 2]

        return {
            "labels": dimensions,
            "datasets": [{
                "label": yAxisLabels,
                "data": data,
                "backgroundColor": 'rgba(54, 162, 235, 0.2)',
                "borderColor": 'rgba(54, 162, 235, 1)',
                "borderWidth": 1
            }],
            "xAxisLabels": [xAxisLabels, headers[1] if len(headers) > 1 else "Dimension 2"],
            "yAxisLabels": [yAxisLabels]
        }

    # Case 5: If data structure is unclear or more complex
    return {"labels": [], "datasets": [], "xAxisLabels": [], "yAxisLabels": []}

# Function to load the datamart mapping into a dictionary
# Path to the CSV file
datamart_mapping_path = '/home/alvcantu/mysite/static/datamart_mapping.csv'
def load_datamart_mapping():
    with open(datamart_mapping_path, mode='r') as file:
        reader = csv.DictReader(file)
        return {row['code']: row['datamart'] for row in reader}

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

# Extracts information for each table in database
db_description = get_db_description()

# Extract sql query from LLM's generated response
def extract_sql_query(text):
    # Define a regex pattern to match SQL queries including those that start with CTEs
    pattern = r'(?i)(WITH\s+.*?AS\s+\(.*?\)\s*(?=(SELECT|INSERT INTO|UPDATE|DELETE FROM|CREATE TABLE|ALTER TABLE|DROP TABLE|TRUNCATE TABLE|GRANT|REVOKE|COMMIT|ROLLBACK|SAVEPOINT|SET TRANSACTION|MERGE))|SELECT|INSERT INTO|UPDATE|DELETE FROM|CREATE TABLE|ALTER TABLE|DROP TABLE|TRUNCATE TABLE|GRANT|REVOKE|COMMIT|ROLLBACK|SAVEPOINT|SET TRANSACTION|MERGE).*?;'
    # Search for the pattern in the text
    match = re.search(pattern, text, re.DOTALL)
    # If a match is found, return the matched string, otherwise return None
    if match:
        return match.group(0)
    return None

# To get html table from a SQL query, executes to DB, transforms to dataframe, then to html.
def get_table_html(sql_query):
    # Check if the query is read-only
    is_read_only, error_message = is_read_only_query(sql_query)
    if not is_read_only:
        return error_message

    try:
        # Connect to MySQL database
        mydb, cursor = get_db_connection()

        # Execute the query
        cursor.execute(sql_query)
        query_results = cursor.fetchall()

        # Convert query results to a pandas DataFrame
        columns = [desc[0] for desc in cursor.description]  # Get column names from cursor description
        df = pd.DataFrame(query_results, columns=columns)

        # Convert DataFrame to HTML
        table_html = df.to_html(table_id="myTable", classes="display")
        return table_html

    except mysql.connector.Error as err:
        return f"Error: {err}"

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'mydb' in locals():
            mydb.close()

# Create data structure diagram for documentation and user view
def create_data_structure_diagram(db_description, output_folder):
    dot = Digraph(comment='Data Structure Diagram')
    dot.attr(rankdir='TB', size='2', dpi='300')
    dot.attr('node', shape='record', style='filled', fillcolor='lightblue')

    def format_data_type(data_type, key_type):
        # Remove parameters from data types like decimal(10,2), varchar(255)
        base_type = data_type.split('(')[0] if '(' in data_type else data_type
        # For enum and set, we'll just use the base type for simplicity
        return f"{base_type} ({key_type})"

    # First pass: Create nodes
    for table_name, columns in db_description.items():
        label = f"{{{table_name}|"
        for col in columns:
            col_name, data_type, _, key_type = col[:4]  # Assuming at least these four elements
            display_type = format_data_type(data_type, key_type)
            label += f"{col_name} : {display_type}|"
        label = label.rstrip('|') + "}"  # Remove trailing | and close the record
        dot.node(table_name, label)

    # Second pass: Create edges based on foreign key relationships
    for table_name, columns in db_description.items():
        for col in columns:
            col_name, data_type = col[0], col[1]
            # Skip non-relational types
            if any(skip_type in data_type.lower() for skip_type in ['date', 'time', 'year', 'timestamp', 'datetime', 'decimal', 'float', 'double', 'real', 'json']):
                continue
            # Check other tables for a primary key matching this column name
            for other_table, other_columns in db_description.items():
                if other_table != table_name:
                    for other_col in other_columns:
                        if other_col[0] == col_name and other_col[3] == 'PRI':
                            # Found a foreign key relationship
                            dot.edge(table_name, other_table,
                                     label=f"{col_name} -> {other_col[0]}",
                                     fontsize='10')

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    # Specify the full path for the output file
    output_path = os.path.join(output_folder, 'data_structure_diagram')
    dot.render(output_path, format='png', cleanup=True, engine='dot')

# Load the datamart mapping when the app starts
datamart_mapping = load_datamart_mapping()
# Converts db_description into diagram thats used in documentation
create_data_structure_diagram(db_description, '/home/alvcantu/mysite/static')

@app.route('/dash_southpark')
def dash_southpark():
    # Connect to MySQL database
    mydb, cursor = get_db_connection()

    # Get full character list for character dropdown menu
    cursor.execute("SELECT character_name FROM SP_DimCharacters;")
    full_char_list = [char[0] for char in cursor.fetchall()]

    # Get full season list for season menu
    cursor.execute("SELECT DISTINCT season FROM SP_DimEpisodes ORDER BY season;")
    season_list = [season[0] for season in cursor.fetchall()]

    # Get user selections
    selected_character = request.args.get('character', full_char_list[0])
    #selected_seasons = request.args.getlist('seasons') or season_list
    selected_seasons = [int(season) for season in request.args.getlist('seasons')] or season_list

    # Create a string of placeholders for the SQL IN clause
    seasons_placeholders = ','.join(['%s'] * len(selected_seasons))

    # ALL SQL queries that are used to extract data and push to front end
    appear_per_season_sql = '''
        SELECT
            e.season AS season,
            COUNT(fec.episode_id) AS appearances
        FROM SP_DimCharacters dc
        JOIN SP_FactEpisodesCharacters fec ON dc.character_id = fec.character_id
        JOIN SP_DimEpisodes e ON fec.episode_id = e.episode_id
        WHERE dc.character_name = %s AND e.season IN ({})
        GROUP BY e.season
        ORDER BY e.season;
        '''.format(seasons_placeholders)

    appear_with_sql = '''
        SELECT
            c2.character_name AS other_character,
            COUNT(*) AS appearance_count
        FROM
            SP_FactEpisodesCharacters fec1
        JOIN
            SP_DimCharacters c1 ON fec1.character_id = c1.character_id
        JOIN
            SP_FactEpisodesCharacters fec2 ON fec1.episode_id = fec2.episode_id
        JOIN
            SP_DimCharacters c2 ON fec2.character_id = c2.character_id
        JOIN
            SP_DimEpisodes e ON fec1.episode_id = e.episode_id
        WHERE
            c1.character_name = %s
            AND c2.character_name != %s
            AND e.season IN ({})
        GROUP BY
            c2.character_id, c2.character_name
        ORDER BY
            appearance_count DESC
        LIMIT 10;
        '''.format(seasons_placeholders)

    epi_list_sql = '''
        SELECT
            e.season AS season_number,
            e.episode_season_num AS episode_number,
            e.title AS episode_title
        FROM
            SP_DimCharacters AS c
        JOIN
            SP_FactEpisodesCharacters AS fec ON c.character_id = fec.character_id
        JOIN
            SP_DimEpisodes AS e ON fec.episode_id = e.episode_id
        WHERE
            c.character_name = %s
            AND e.season IN ({})
        ORDER BY e.season, e.episode_season_num;
        '''.format(seasons_placeholders)

    char_role_sql = '''
    SELECT role FROM SP_DimCharacters
    WHERE character_name = %s;
    '''

    # Execute queries with user selections
    cursor.execute(appear_per_season_sql, (selected_character, *selected_seasons))
    appearances_per_season = cursor.fetchall()

    cursor.execute(appear_with_sql, (selected_character, selected_character, *selected_seasons))
    appears_with = cursor.fetchall()

    cursor.execute(epi_list_sql, (selected_character, *selected_seasons))
    episode_list = cursor.fetchall()

    cursor.execute(char_role_sql, (selected_character,))
    character_role = cursor.fetchall()

    # Close database connection
    cursor.close()
    mydb.close()

    # Render template with data
    return render_template('dash_southpark.html',
                           full_char_list=full_char_list,
                           season_list=season_list,
                           selected_character=selected_character,
                           selected_seasons=selected_seasons,
                           appearances_per_season=appearances_per_season,
                           appears_with=appears_with,
                           episode_list=episode_list,
                           character_role=character_role)

@app.route('/dash_stocks')
def dash_stocks():

    # Connect to MySQL database
    mydb, cursor = get_db_connection()

    # Fetch all company names used to create user selection list
    cursor.execute("SELECT DISTINCT name FROM ST_DimCompany;")
    company_names = [row[0] for row in cursor.fetchall()]

    company_data = {}

    for company in company_names:
        # Fetch company info using user selection as %s
        cursor.execute("""
            SELECT name, country, website, industry, currency, summary
            FROM ST_DimCompany
            WHERE name = %s
        """, (company,))
        company_info = cursor.fetchone()

        # Fetch price data using user selection as %s
        cursor.execute("""
            SELECT
                f.date as date,
                CASE
                    WHEN f.date < CURDATE() THEN f.close_price
                    ELSE f.forecast_price_arima
                END AS price,
                CASE
                    WHEN f.date < CURDATE() THEN 'Actual'
                    ELSE 'Forecast'
                END AS price_type
            FROM
                ST_FactPrices as f
            JOIN
                ST_DimCompany as d ON f.ticker=d.ticker
            WHERE
                d.name = %s
            ORDER BY
                date;
        """, (company,))
        price_data = cursor.fetchall()

        # Convert date objects to strings and ensure all data is JSON-serializable and readable by front-end
        prices = [
            {
                'date': date.isoformat() if isinstance(date, datetime) else str(date),
                'price': float(price) if price is not None else None,  # Handle None values
                'price_type': price_type
            }
            for date, price, price_type in price_data
        ]
        # Replace spaces with underscores for PDF filename
        pdf_filename = f"stock_report_{company.replace(' ', '_')}.pdf"
        # Generate the URL for the PDF file
        company_pdf = url_for('static', filename=pdf_filename)

        # Store all data including PDF URL in the dictionary
        company_data[company] = {
            'name': company_info[0],
            'country': company_info[1],
            'website': company_info[2],
            'industry': company_info[3],
            'currency': company_info[4],
            'summary': company_info[5],
            'prices': prices,
            'pdf_url': company_pdf
        }

    return render_template('dash_stocks.html',
                           company_names=company_names,
                           company_data=company_data)    

@app.route('/dash_self_service', methods=['GET', 'POST'])
def dash_self_service():
    user_query = ''
    sql_query = ''
    data_output = ''
    selected_visual = 'Table' # Default visualization type

    if request.method == 'POST':
        user_query = request.form.get('user_query', '')
        selected_visual = request.form.get('selected_visual', 'Table')

        # Function to generate SQL query using OpenRouter API
        prompt = f"""
        Given the following database schema with column comments for context:
        {db_description}

        Generate a query for this request:
        {user_query}
        """

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        }
        data = {
            "model": "openrouter/auto",  # You can change this to another model if needed
            "messages": [
                {"role": "system", "content": "You are a MySQL server query generator that outputs code ready to executed. Only included the needed columns in the query."},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        sql_query_unclean = response.json()['choices'][0]['message']['content']

        # Extract only the query from the sql query response
        sql_query = extract_sql_query(sql_query_unclean)
        # Add limit to the query to prevent data from being too large
        sql_query = sql_query.rstrip(';') + ' LIMIT 6900;'

        # Connect to MySQL database
        mydb, cursor = get_db_connection()

        # Execute the SQL query and get the data output
        cursor.execute(sql_query)
        raw_data_output = cursor.fetchall()

        if selected_visual == 'Table':
            # Prepare data for DataTable, get_table_html function already checks if the query is read-only
            data_output = get_table_html(sql_query)

        else:
            # Check if the query is read-only
            is_read_only, error_message = is_read_only_query(sql_query)
            if not is_read_only:
                return error_message
            else:
                # Prepare the data for Chart.js using the dynamic function
                data_output = prepare_data_for_chart(raw_data_output)
        
    
    return render_template('dash_self_service.html',
                           selected_visual=selected_visual,
                           sql_query=sql_query,
                           user_query=user_query,
                           data_output=data_output)

@app.route('/documentation')
def documentation():
    paths = {
        'web_app': '/home/alvcantu/mysite/web_app.py',
        'presentation_generator': '/home/alvcantu/presentation_generator.py',
        # South Park files
        'run_southpark': '/home/alvcantu/run_southpark.py',
        'character_details_spider': '/home/alvcantu/southpark/southpark/spiders/character_details_spider.py',
        'episodes_details_spider': '/home/alvcantu/southpark/southpark/spiders/episodes_details_spider.py',
        'episode_loop_spider': '/home/alvcantu/southpark/southpark/spiders/episode_loop_spider.py',
        'etl_southpark': '/home/alvcantu/southpark/etl/etl_southpark.py',
        'etl_stg_southpark': '/home/alvcantu/southpark/etl/etl_stg_southpark.py',
        'dash_southpark': '/home/alvcantu/mysite/templates/dash_southpark.html',
        # Stocks files
        'run_stocks': '/home/alvcantu/run_stocks.py',
        'company_list_spider': '/home/alvcantu/stocks/stocks/spiders/company_list_spider.py',
        'etl_ST_DimCompany':'/home/alvcantu/stocks/etl/etl_ST_DimCompany.py',
        'etl_ST_FactPrices':'/home/alvcantu/stocks/etl/etl_ST_FactPrices.py',
        'etl_ST_FactPrices_Forecast':'/home/alvcantu/stocks/etl/etl_ST_FactPrices_Forecast.py',
        'pdf_gen_stocks':'/home/alvcantu/stocks/etl/pdf_gen_stocks.py',
        'dash_stocks': '/home/alvcantu/mysite/templates/dash_stocks.html',
        # Online retail files
        'etl_online_retail': '/home/alvcantu/online_retail/etl_online_retail.py',
        'create_mlmodel_online_retail': '/home/alvcantu/online_retail/create_mlmodel_online_retail.py'
    }

    replacements = [
        ('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', 'openrouter_api_key_goes_here'),
        ('h63Efp09-d', 'pw_goes_here'),
        ('alvcantu@icloud.com', 'my_email_goes_here'),
        ('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','sendgrid_api_key_goes_here')
    ]

    def extract_and_sanitize_code(path):
        try:
            with open(path, 'r') as file:
                code = file.read()
            for old, new in replacements:
                code = code.replace(old, new)
            return code
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    template_variables = {key: extract_and_sanitize_code(path) for key, path in paths.items()}

    return render_template('documentation.html', datamart_mapping=datamart_mapping,**template_variables)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)