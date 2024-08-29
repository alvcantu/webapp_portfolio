import mysql.connector
from graphviz import Digraph

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

# Create data structure diagram for documentation and user view
def create_data_structure_diagram(db_description, output_folder):
    dot = Digraph(comment='Data Structure Diagram')
    dot.attr(rankdir='TB', size='2', dpi='300')
    dot.attr('node', shape='record', style='filled', fillcolor='lightblue')

    # First pass: Create nodes
    for table_name, columns in db_description.items():
        label = f"{{{table_name}|"
        for col in columns:
            # Assuming col structure is [column_name, data_type, ... other info]
            col_name, data_type, _, col_key = col[:4]  # Unpack assuming at least 4 elements
            
            # Handle the new data type format
            if '(' in data_type:  # Check if it's a type with parameters like decimal(10,2)
                data_type_for_display = data_type.split('(')[0] + '(' + col_key + ')'
            else:
                data_type_for_display = data_type + ' (' + col_key + ')'
            
            label += f"{col_name} : {data_type_for_display}|"
        label = label.rstrip('|') + "}"  # Remove trailing | and close the record
        dot.node(table_name, label)

    # Second pass: Create edges based on foreign key relationships
    for table_name, columns in db_description.items():
        for col in columns:
            col_name, data_type = col[0], col[1]
            # Skip date columns and potentially others not needing relationship checks
            if 'date' in data_type.lower() or 'decimal' in data_type.lower():
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
# def create_data_structure_diagram(db_description, output_folder):
#     dot = Digraph(comment='Data Structure Diagram')
#     dot.attr(rankdir='TB', size='2', dpi='300')
#     dot.attr('node', shape='record', style='filled', fillcolor='lightblue')

#     # First pass: Create nodes
#     for table_name, columns in db_description.items():
#         label = f"{{{table_name}|"
#         label += "|".join([f"{col[0]} : {col[1].decode()} ({col[3]})" for col in columns])
#         label += "}"
#         dot.node(table_name, label)

#     # Second pass: Create edges based on foreign key relationships
#     for table_name, columns in db_description.items():
#         for col in columns:
#             # Skip date columns
#             if 'date' in col[1].decode().lower():
#                 continue
#             # Check other tables for a primary key matching this column name
#             for other_table, other_columns in db_description.items():
#                 if other_table != table_name:
#                     for other_col in other_columns:
#                         if other_col[0] == col[0] and other_col[3] == 'PRI':
#                             # Found a foreign key relationship
#                             dot.edge(table_name, other_table,
#                                      label=f"{col[0]} -> {other_col[0]}",
#                                      fontsize='10')

#     # Create the output folder if it doesn't exist
#     os.makedirs(output_folder, exist_ok=True)
#     # Specify the full path for the output file
#     output_path = os.path.join(output_folder, 'data_structure_diagram')
#     dot.render(output_path, format='png', cleanup=True, engine='dot')

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
