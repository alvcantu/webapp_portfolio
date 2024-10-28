import pandas as pd
import numpy as np
import json
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder

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


# Initialize LabelEncoder
le = LabelEncoder()

# Convert ENUM and other categorical data to category type for better memory usage and performance
# Here, we'll define which keys should be treated as categories
categorical_keys = ['job', 'marital', 'education', 'default_credit', 'housing', 'loan', 'contact', 'month', 'poutcome']

# Encode categorical variables, after this loop, user_input will have numerical labels for categorical data
for key in user_input.keys():
    if key in categorical_keys:
        # Transform the categorical data into numerical labels
        user_input[key] = le.fit_transform([user_input[key]])[0]

# Convert dict to DataFrame
user_input_df = pd.DataFrame([user_input])

# Load model
model = xgb.Booster()
model.load_model('bank_marketing/ml_model_bank_marketing.json')

# Convert to DMatrix and predict
X = xgb.DMatrix(user_input_df)
prediction = model.predict(X)


# Final determination for customer
customer_determination = ''
if prediction[0] >0.5:
    customer_determination = 'Yes'
else:
    customer_determination = 'No'

print(prediction)
print(customer_determination)
