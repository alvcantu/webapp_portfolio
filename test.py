import json
import pandas as pd
import xgboost as xgb

# Setting empty strings that get filled with form data later
prediction = ''
customer_approval = ''

# Values to inserted in dataframe, will come fron front-end in the future.
user_input = {
    'age': 32,  # Default to 0 if not provided or empty, round to 2 decimals
    'job': "student",  
    'marital': "married",  
    'education': "secondary",  
    'default_credit': "no",  # Has credit in default?
    'balance': 2500,  # Account balance, default to 0
    'housing': "yes",  # Has housing loan?
    'loan': "no",  # Has personal loan?
    'contact': "cellular",  # Contact communication type
    'month': "feb",  # Last contact month of year
    'campaign': 0,  # Number of contacts performed during this campaign and for this client
    'pdays': 0,  # Number of days that passed by after the client was last contacted from a previous campaign
    'previous': 0,  # Number of contacts performed before this campaign and for this client
    'poutcome': "nonexistent"  # Outcome of the previous marketing campaign
}

# Load the label encoding from the JSON file
with open('bank_marketing/ml_model_label_enconding_bank_marketing.json', 'r') as json_file:
    label_encoding = json.load(json_file)

# Define the keys to be treated as categorical
categorical_keys = ['job', 'marital', 'education', 'default_credit', 'housing', 'loan', 'contact', 'month', 'poutcome']

# Encode categorical variables using the loaded label encoding dictionary
for key in user_input.keys():
    if key in categorical_keys:
        # Use the label encoding mapping from the JSON file
        user_input[key] = label_encoding[key].get(user_input[key], -1)  # -1 for unknown values not in the mapping


# Convert dict to DataFrame
user_input_df = pd.DataFrame([user_input])

print(user_input_df.head())

# Load model
model = xgb.Booster()
model.load_model('bank_marketing/ml_model_bank_marketing.json')

# Convert to DMatrix
X = xgb.DMatrix(user_input_df)

#Predict and convert for evaluation
prediction = model.predict(X)
prediction = round(prediction[0], 2)*100

# Final determination for customer
customer_determination = ''
if prediction >50:
    customer_approval = 'Yes'
else:
    customer_approval = 'No'

# Convert prediction to string with % sign
prediction = str(prediction) + '%'

print("Prediction:")
print(prediction)
print(customer_determination)