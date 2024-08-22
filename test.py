import os
import mysql.connector
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager as fm


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

# Function to create metrics and graphs for south park slide
def create_south_park_elements():
    # Get the database connection and cursor
    conn, cursor = get_db_connection()

    # Gather randomized character_id
    cursor.execute('''
    SELECT 
        character_id 
    FROM 
        SP_DimCharacters
    ORDER BY 
        RAND()
    LIMIT 1;''')
    random_character_id = cursor.fetchone()[0]

    # Gather data for appearances per season
    cursor.execute(f'''
    SELECT
        e.season AS season,
        COUNT(fec.episode_id) AS appearances
    FROM SP_DimCharacters dc
    JOIN SP_FactEpisodesCharacters fec ON dc.character_id = fec.character_id
    JOIN SP_DimEpisodes e ON fec.episode_id = e.episode_id
    WHERE dc.character_id = %s
    GROUP BY e.season
    ORDER BY e.season;
    ''', (random_character_id,))
    appearances_per_season = cursor.fetchall()

    # Gather character_name and role
    cursor.execute(f'''
    SELECT character_name, role FROM SP_DimCharacters
    WHERE character_id = %s;
    ''',(random_character_id,))
    character_info = cursor.fetchall()

    # Creating the graph and saving it in static folder
    # Extract data for plotting
    seasons = [row[0] for row in appearances_per_season]
    appearances = [row[1] for row in appearances_per_season]

    # Plotting the vertical bar graph
    plt.figure(figsize=(10, 6))
    bars = plt.bar(seasons, appearances, color='skyblue')

    # Adding appearance counts above each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2.0, height, str(height), ha='center', va='bottom')

    # Adding title and labels
    character_name = character_info[0][0]
    plt.title(f'Appearances of {character_name} per Season')
    plt.xlabel('Season')
    plt.ylabel('Number of Appearances')

    # Define the save path
    save_directory = '/home/alvcantu/mysite/static/presentation_graphs'
    os.makedirs(save_directory, exist_ok=True)
    save_path = os.path.join(save_directory, f'southpark_appearances_per_season.png')

    # Save the plot
    plt.savefig(save_path)

    # LLM writes summary of south park character
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        },
        data=json.dumps({
        "model": "openrouter/auto",
        "messages": [
            {"role": "system", "content": "Write 3 bullet points about the attached South Park character information."},
            {"role": "user", "content": f"{character_info}"}
        ]
        })
    )
    # Parsing response to json
    response_data = response.json()
    # Extracting actual response from json
    llm_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No content found')

    return character_name, llm_response

create_south_park_elements()