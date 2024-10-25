import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier


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


sql_query_extract = '''
SELECT * FROM BM_FactCustomers LIMIT 1;
'''

# Fetch data
mydb, cursor = get_db_connection()
cursor.execute(sql_query_extract)
data = cursor.fetchall()
columns = [i[0] for i in cursor.description]  # Get column names

# Convert to DataFrame
df = pd.DataFrame(data, columns=columns)

# Only extract the needed features
features = df.drop(columns=['subscribed_y', 'duration','customer_id'])

# Values to inserted in dataframe, will come fron front-end in the future.
user_input = {
    'age': 35,  # Example age
    'job': 'tertiary',  # Example job
    'marital': 'married',  # Example marital status
    'education': 'university',  # Example education level
    'default_credit': 'no',  # Has credit in default?
    'balance': 2345.0,  # Account balance
    'housing': 'yes',  # Has housing loan?
    'loan': 'no',  # Has personal loan?
    'contact': 'cellular',  # Contact communication type
    'month': 'jul',  # Last contact month of year
    'campaign': 3,  # Number of contacts performed during this campaign and for this client
    'pdays': 999,  # Number of days that passed by after the client was last contacted from a previous campaign (999 means client was not previously contacted)
    'previous': 1,  # Number of contacts performed before this campaign and for this client
    'poutcome': 'success'  # Outcome of the previous marketing campaign
}

# adding user_input
features.loc[0] = pd.Series(user_input)

# Convert ENUM and other categorical data to category type for better memory usage and performance
for col in features.columns:
    if features[col].dtype == 'object':  # This will catch both ENUM and VARCHAR
        features[col] = features[col].astype('category')

# Encode categorical variables
le = LabelEncoder()
for column in features.select_dtypes(include=['category', 'object']):
    features[column] = le.fit_transform(features[column])

print(features.head())

# # Import the model
# model = xgb.XGBRegressor()
# model.load_model('bank_marketing/ml_model_classification_bank_marketing.json')

# # Apply the model to the data
# X = df[features]
# predictions = model.predict(X)
# predictions = 0

# # Convert predictions to a DataFrame if it's not already one
# final_prediction = 'yes' if predictions[0] == 1 else 'no'




