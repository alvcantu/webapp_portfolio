import pandas as pd
import re

#CLEANS AND ADDS NEW COLUMNS TO raw_character_details, OUTPUTING stg_character_details

# Define the file path
path_character_details = '/home/alvcantu/southpark/etl/raw_character_details.csv'
#convert to dataframe
df_character_details = pd.read_csv(path_character_details)

# Creating a dictionary with Sheila's data
sheila_info = {
    'character_name': 'Sheila Broflovski',
    'role': 'Sheila made her first appearance in the season one episode "Death" (where she was originally named Carol), and she exhibits several traits commonly associated with those of a stereotypical Jewish mother. In the episode "Its a Jersey Thing", it is revealed that Sheila was originally from New Jersey, where she was known as "S-Wow Tittybang", and that she and Gerald moved to South Park to avoid having their newly conceived child grow up there. Apart from being briefly appointed to the fictional federal position of "Secretary of Offense" under the Clinton Administration, Sheila is a stay-at-home mother. In earlier seasons, Sheila often spearheaded public opposition to things she deemed harmful to children or to the Jewish community. She led a group to New York City to protest Terrance and Phillip, a Canadian comedy duo whose television shows toilet humor is what she believed to be a negative influence on Kyle.[59] Her outrage escalated in South Park: Bigger, Longer & Uncut when she further protested Terrance and Phillip by forming Mothers Against Canada, which eventually instigated a war between Canada and the United States making her one of the main antagonists of the film. At the climax of the film, she takes her crusade against the duo to the extreme by shooting Terrance and Phillip despite her sons protests, which fulfills an apocalyptic prophecy allowing Satan, his minions, and his ex-lover Saddam Hussein to invade Earth. This aspect has been toned down in recent years, and is more or less completely absent from newer episodes.'
}
#Create new staging dataframe with Sheila added
df_character_details_stg = df_character_details._append(sheila_info, ignore_index=True)

# Function to remove brackets and their contents
def remove_all_brackets(text):
    return re.sub(r'\([^)]*\)|\[[^]]*\]', '', text).strip()

def remove_square_brackets(text):
    return re.sub(r'\[[^]]*\]', '', text).strip()

# Function to extract the first two sentences only
def keep_first_two_sentences(text):
    # Split the text into sentences using a regular expression to handle sentence boundaries
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)

    # Join the first two sentences, ensuring proper spacing
    if len(sentences) >= 2:
        result = sentences[0] + ' ' + sentences[1]
    else:
        result = ' '.join(sentences)  # Return all if less than 2 sentences
    
    return result.strip()



#Remove cases where column names appear as values
df_character_details_stg = df_character_details_stg[
                                (df_character_details_stg['character_name'] != 'character_name') &
                                (df_character_details_stg['role'] != 'role')
                            ]

# Change 'Gerald and Sheila Broflovski' to 'Gerald Broflovski'
df_character_details_stg.loc[df_character_details_stg['character_name'] == 'Gerald and Sheila Broflovski', 'character_name'] = 'Gerald Broflovski'

# Remove brackets and their contents, all brackets from character_name, square from only role.
df_character_details_stg['character_name'] = df_character_details_stg['character_name'].apply(remove_all_brackets)
df_character_details_stg['role'] = df_character_details_stg['role'].apply(remove_square_brackets)
df_character_details_stg['role'] = df_character_details_stg['role'].apply(keep_first_two_sentences)

# Function to determine character_id, default is first name. Conditions for specific names apply.
def get_character_id(name):
    # Handle cases with quotations
    if re.search(r'".+?"', name):
        return re.search(r'".+?"', name).group(0).strip('"')
    # Handle cases with '/'
    if '/' in name:
        return name.split('/')[1].strip().split()[0]
    # Handle specific cases where character_id is the same as character_name
    specific_cases = {
        'PC Principal', 'Strong Woman', 'Terrance and Phillip',
        'Big Gay Al', 'Father Maxi', 'Officer Barbrady',
        'Ugly Bob', 'Red McArthur', 'Scott Malkinson',
        'Kevin Mephesto', 'Kevin McKornick', 'Kevin McCormick'
    }
    if name in specific_cases:
        return name
    #Handles unique Lu Kim case
    if name == 'Tuong Lu Kim':
        return 'Lu Kim'
    # Handle cases with honorifics
    if re.match(r'^(Mr\.|Mrs\.|Ms\.|Dr\.)', name):
        return ' '.join(name.split()[:2])
    # Default case: take the first word
    return name.split()[0]

# Create new column 'character_id'
df_character_details_stg['character_id'] = df_character_details_stg['character_name'].apply(get_character_id)

# Save the dataframe as a CSV file
df_character_details_stg.to_csv('etl/stg_character_details.csv', index=False)

print("File 'stg_character_details.csv' has been created successfully.")
