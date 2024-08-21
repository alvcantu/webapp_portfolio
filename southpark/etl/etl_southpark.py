import pandas as pd
from urllib.parse import urlparse
import ast
import re
from html import unescape
import mysql.connector
from mysql.connector import Error

#EXTRACT
# Define the file path
path_episode_details = '/home/alvcantu/southpark/etl/raw_episode_details.csv'
path_character_details = '/home/alvcantu/southpark/etl/stg_character_details.csv'
path_episode_loop = '/home/alvcantu/southpark/etl/raw_episode_loop.csv'

#convert to dataframe
df_episode_details = pd.read_csv(path_episode_details)
df_characters = pd.read_csv(path_character_details)
df_episode_loop = pd.read_csv(path_episode_loop)


#<------------------------------------------------------------------------>

#TRANSFORM
# Perform a full outer join on title_link to have one df_episode
df_episodes = df_episode_details.merge(df_episode_loop[['title_link', 'summary', 'mentioned_character_ids']], on='title_link', how='left')

# Function to extract season and episode number from column prod_code
def extract_season_episode(prod_code):
    if prod_code.isdigit():
        season = int(prod_code[:-2])  # All except the last two digits
        episode = int(prod_code[-2:])  # The last two digits
        return season, episode
    else:
        return 0, 0
# Apply the function to the DataFrame to add two new columns
df_episodes['season'], df_episodes['episode_season_num'] = zip(*df_episodes['prod_code'].apply(extract_season_episode))

# Function to remove rows where any value equals its column title
def remove_rows_with_titles(df):
    column_titles = df.columns.tolist()  # Automatically get column titles
    for title in column_titles:
        # Remove rows where the value in the column equals the column title
        df = df[df[title] != title]
    return df

# Apply the function to the DataFrame
df_episodes = remove_rows_with_titles(df_episodes)

# Convert the data types
df_episodes['episode_id'] = df_episodes['episode_id'].astype(int)
df_episodes['title'] = df_episodes['title'].astype(str)
df_episodes['url'] = df_episodes['title_link'].astype(str) #rename for clarity
df_episodes['date'] = df_episodes['date'].astype(str)
df_episodes['prod_code'] = df_episodes['prod_code'].astype(str)
df_episodes['season'] = df_episodes['season'].astype(int)
df_episodes['episode_season_num'] = df_episodes['episode_season_num'].astype(int)
df_episodes['summary'] = df_episodes['summary'].astype(str)
# Convert the mentioned_character_ids to a list
df_episodes['mentioned_character_ids'] = df_episodes['mentioned_character_ids'].apply(ast.literal_eval)

#Cleaning summary column
def clean_html(html_text):
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_text)
    # Unescape HTML entities
    clean_text = unescape(clean_text)
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    return clean_text

# Assuming you have a pandas DataFrame named 'df' with a column 'summary'
df_episodes['summary'] = df_episodes['summary'].apply(clean_html)

#Create df fact, normalizing mentioned_character_id's into one character id with multiple episode_id's
#Dropping columns
df_fact_prep = df_episodes[['episode_id', 'mentioned_character_ids']]
#Normalization
df_fact = df_fact_prep.explode('mentioned_character_ids').rename(columns={'mentioned_character_ids': 'character_id'})

#Dropping non needed colums
df_episodes = df_episodes[['episode_id','title','url','date','prod_code','season','episode_season_num','summary']]

def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def check_data_quality_df_episodes(df):
    errors = {}

    # Check episode_id
    if df['episode_id'].isnull().any():
        errors['episode_id_null'] = df[df['episode_id'].isnull()]['episode_id'].tolist()
    if not pd.api.types.is_numeric_dtype(df['episode_id']):
        errors['episode_id_not_numeric'] = df['episode_id'].tolist()
    if not df['episode_id'].is_unique:
        errors['episode_id_not_unique'] = df[df['episode_id'].duplicated(keep=False)]['episode_id'].tolist()

    # Check title
    if not df['title'].is_unique:
        errors['title_not_unique'] = df[df['title'].duplicated(keep=False)]['episode_id'].tolist()

    # Check season and episode_season_num
    if df['season'].isnull().any() or not pd.api.types.is_numeric_dtype(df['season']):
        errors['season_invalid'] = df[(df['season'].isnull()) | (pd.api.types.is_numeric_dtype(df['season']))]['episode_id'].tolist()
    if df['episode_season_num'].isnull().any() or not pd.api.types.is_numeric_dtype(df['episode_season_num']):
        errors['episode_season_num_invalid'] = df[(df['episode_season_num'].isnull()) | (pd.api.types.is_numeric_dtype(df['episode_season_num']))]['episode_id'].tolist()

    # Check summary (assuming summary column exists)
    if 'summary' in df.columns:
        if not df['summary'].apply(lambda x: isinstance(x, str)).all():
            errors['summary_not_string'] = df[~df['summary'].apply(lambda x: isinstance(x, str))]['episode_id'].tolist()
        if not df['summary'].is_unique:
            errors['summary_not_unique'] = df[df['summary'].duplicated(keep=False)]['episode_id'].tolist()

    # Check dates
    if not df['date'].notna().all():
        errors['date_invalid'] = df[df['date'].isna()]['episode_id'].tolist()
    if not df['date'].is_unique:
        errors['date_not_unique'] = df[df['date'].duplicated(keep=False)]['episode_id'].tolist()

    # Check url
    invalid_urls = ~df['url'].apply(is_url)
    if invalid_urls.any():
        errors['url_invalid'] = df[invalid_urls]['episode_id'].tolist()
    if not df['url'].is_unique:
        errors['url_not_unique'] = df[df['url'].duplicated(keep=False)]['episode_id'].tolist()

    # Additional common data quality checks
    null_columns = df.columns[df.isnull().any()].tolist()
    if null_columns:
        errors['null_values'] = {col: df[df[col].isnull()]['episode_id'].tolist() for col in null_columns}

    non_standard_types = df.applymap(lambda x: not isinstance(x, (int, float, str)))
    if non_standard_types.any().any():
        errors['non_standard_types'] = {col: df[non_standard_types[col]]['episode_id'].tolist() for col in non_standard_types.columns if non_standard_types[col].any()}

    return errors

def check_data_quality_df_characters(df):
    errors = {}

    # Check if all required columns are present
    required_columns = ['character_id', 'character_name', 'role']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors['missing_columns'] = missing_columns
        return errors  # Return early if columns are missing

    # Check character_id
    if not df['character_id'].apply(lambda x: isinstance(x, str)).all():
        errors['character_id_not_string'] = df[~df['character_id'].apply(lambda x: isinstance(x, str))]['character_id'].tolist()
    if not df['character_id'].is_unique:
        errors['character_id_not_unique'] = df[df['character_id'].duplicated(keep=False)]['character_id'].tolist()

    # Check character_name
    if not df['character_name'].apply(lambda x: isinstance(x, str)).all():
        errors['character_name_not_string'] = df[~df['character_name'].apply(lambda x: isinstance(x, str))]['character_id'].tolist()
    if not df['character_name'].is_unique:
        errors['character_name_not_unique'] = df[df['character_name'].duplicated(keep=False)]['character_id'].tolist()

    # Check role
    if not df['role'].apply(lambda x: isinstance(x, str)).all():
        errors['role_not_string'] = df[~df['role'].apply(lambda x: isinstance(x, str))]['character_id'].tolist()

    # Check for null values
    null_columns = df.columns[df.isnull().any()].tolist()
    if null_columns:
        errors['null_values'] = {col: df[df[col].isnull()]['character_id'].tolist() for col in null_columns}

    return errors

def check_data_quality_df_fact(df):
    errors = {}

    # Check if all required columns are present
    required_columns = ['episode_id', 'character_id']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors['missing_columns'] = missing_columns
        return errors  # Return early if columns are missing

    # Check for empty values
    for column in required_columns:
        empty_values = df[df[column].isnull() | (df[column] == '')]
        if not empty_values.empty:
            errors[f'{column}_empty'] = empty_values.index.tolist()

    # Check if episode_id is integer type
    non_int_episode_ids = df[~df['episode_id'].apply(lambda x: isinstance(x, int) or (isinstance(x, float) and x.is_integer()))]
    if not non_int_episode_ids.empty:
        errors['episode_id_not_int'] = non_int_episode_ids.index.tolist()

    # Check if character_id is string type
    non_string_character_ids = df[~df['character_id'].apply(lambda x: isinstance(x, str))]
    if not non_string_character_ids.empty:
        errors['character_id_not_string'] = non_string_character_ids.index.tolist()

    return errors

#Apply all checks to dataframes
errors_df_episodes = check_data_quality_df_episodes(df_episodes)
errors_df_characters = check_data_quality_df_characters(df_characters)
errors_df_fact = check_data_quality_df_fact(df_fact)

#<------------------------------------------------------------------------>

#LOAD

#Function to create tables if non existent in mySQL and add values incrementally
def create_mysql_tables_and_insert_data(df_episodes, df_characters, df_fact):
    try:
        # MySQL connection parameters
        connection = mysql.connector.connect(
          host="alvcantu.mysql.pythonanywhere-services.com",
          user="alvcantu",
          password="h63Efp09-d",
          database="alvcantu$default"
        )

        cursor = connection.cursor()

        # Create SP_DimCharacters table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SP_DimCharacters (
            character_name VARCHAR(255) NOT NULL UNIQUE COMMENT 'Full name of the character',
            role VARCHAR(255) NOT NULL COMMENT 'Role of the character in the series',
            character_id VARCHAR(255) PRIMARY KEY COMMENT 'Unique identifier and nickname for each character',
            CONSTRAINT chk_character_id CHECK (character_id <> ''),
            CONSTRAINT chk_character_name CHECK (character_name <> ''),
            CONSTRAINT chk_role CHECK (role <> '')
        ) COMMENT 'Dimension table containing information about characters in the South Park TV series. Each row represents a unique character with their ID, name, and role.'
        """)

        # Create SP_DimEpisodes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SP_DimEpisodes (
            episode_id INT PRIMARY KEY COMMENT 'Unique identifier for each episode',
            title VARCHAR(255) NOT NULL UNIQUE COMMENT 'Title of the episode',
            url VARCHAR(255) NOT NULL UNIQUE COMMENT 'Wikipedia URL link to the episode information',
            date DATE NOT NULL COMMENT 'Original air date of the episode',
            prod_code VARCHAR(255) COMMENT 'Production code of the episode',
            season INT NOT NULL COMMENT 'Season number of the episode',
            episode_season_num INT NOT NULL COMMENT 'Episode number within the season',
            summary TEXT COMMENT 'Brief summary or description of the episode',
            CONSTRAINT chk_title CHECK (title <> ''),
            CONSTRAINT chk_url CHECK (url <> ''),
            CONSTRAINT chk_season CHECK (season >= 0),
            CONSTRAINT chk_episode_season_num CHECK (episode_season_num >= 0)
        ) COMMENT 'Dimension table containing information about South Park TV episodes. Each row represents a unique episode with details such as title, air date, season, and summary.'
        """)

        # Create SP_FactEpisodesCharacters table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SP_FactEpisodesCharacters (
            episode_id INT COMMENT 'Foreign key referencing SP_DimEpisodes.episode_id',
            character_id VARCHAR(255) COMMENT 'Foreign key referencing SP_DimCharacters.character_id',
            PRIMARY KEY (episode_id, character_id),
            FOREIGN KEY (episode_id) REFERENCES SP_DimEpisodes(episode_id),
            FOREIGN KEY (character_id) REFERENCES SP_DimCharacters(character_id)
        ) COMMENT 'Fact table linking characters to episodes. Each row represents an appearance of a character in a specific episode, establishing many-to-many relationships between characters and episodes.'
        """)

        # Insert new characters
        cursor.execute("SELECT character_id FROM SP_DimCharacters")
        existing_characters = set(row[0] for row in cursor.fetchall())
        new_characters = df_characters[~df_characters['character_id'].isin(existing_characters)]

        if not new_characters.empty:
            character_values = [tuple(row) for row in new_characters.itertuples(index=False)]
            cursor.executemany("""
            INSERT INTO SP_DimCharacters (character_name, role, character_id)
            VALUES (%s, %s, %s)
            """, character_values)

        # Insert new episodes
        cursor.execute("SELECT episode_id FROM SP_DimEpisodes")
        existing_episodes = set(row[0] for row in cursor.fetchall())
        new_episodes = df_episodes[~df_episodes['episode_id'].isin(existing_episodes)]

        if not new_episodes.empty:
            episode_values = [tuple(row) for row in new_episodes.itertuples(index=False)]
            cursor.executemany("""
            INSERT INTO SP_DimEpisodes (episode_id, title, url, date, prod_code, season, episode_season_num, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, episode_values)

        # Insert new fact data
        cursor.execute("SELECT episode_id, character_id FROM SP_FactEpisodesCharacters")
        existing_facts = set(tuple(row) for row in cursor.fetchall())
        new_facts = df_fact[~df_fact.apply(tuple, axis=1).isin(existing_facts)]

        if not new_facts.empty:
            fact_values = [tuple(row) for row in new_facts.itertuples(index=False)]
            cursor.executemany("""
            INSERT INTO SP_FactEpisodesCharacters (episode_id, character_id)
            VALUES (%s, %s)
            """, fact_values)

        connection.commit()
        print("Tables created and data inserted successfully.")

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Check if all error variables are empty
if not errors_df_episodes and not errors_df_characters and not errors_df_fact:
    create_mysql_tables_and_insert_data(df_episodes, df_characters, df_fact)
else:
    print("Data quality issues found. Please resolve before proceeding.")


