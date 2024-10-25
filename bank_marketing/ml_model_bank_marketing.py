import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as json
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from bayes_opt import BayesianOptimization
import json


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
SELECT * FROM BM_FactCustomers;
'''

# Fetch data
mydb, cursor = get_db_connection()
cursor.execute(sql_query_extract)
data = cursor.fetchall()
columns = [i[0] for i in cursor.description]  # Get column names

# Convert to DataFrame
df = pd.DataFrame(data, columns=columns)

# Convert ENUM and other categorical data to category type for better memory usage and performance
for col in df.columns:
    if df[col].dtype == 'object':  # This will catch both ENUM and VARCHAR
        df[col] = df[col].astype('category')

# Assuming 'duration' should not be used in the model as per following documentation:
# Duration: last contact duration, in seconds (numeric). Important
# note: this attribute highly affects the output target (e.g., if
# duration=0 then y='no'). Yet, the duration is not known before a call
# is performed. Also, after the end of the call y is obviously known.
# Thus, this input should only be included for benchmark purposes and
# should be discarded if the intention is to have a realistic
# predictive model.

# Assuming 'df' is already loaded with your data

# Define features and target
features = df.drop(columns=['subscribed_y', 'duration', 'customer_id'])
target = df['subscribed_y']

# Encode categorical variables
categorical_columns = features.select_dtypes(include=['object']).columns
encoders = {}
for column in categorical_columns:
    le = LabelEncoder()
    features[column] = le.fit_transform(features[column])
    encoders[column] = le.classes_

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

# Initialize XGBoost model
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test)

def xgb_evaluate(max_depth, gamma, colsample_bytree):
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'max_depth': int(max_depth),
        'subsample': 0.8,
        'eta': 0.1,
        'gamma': gamma,
        'colsample_bytree': colsample_bytree,
        'silent': 1
    }
    
    cv_result = xgb.cv(params, dtrain, num_boost_round=100, nfold=5,
                       metrics='auc', early_stopping_rounds=50, seed=42)
    
    return cv_result['test-auc-mean'].iloc[-1]

# Setting up the Bayesian Optimizer
xgb_bo = BayesianOptimization(
    xgb_evaluate, 
    {'max_depth': (3, 10),
     'gamma': (0, 5),
     'colsample_bytree': (0.5, 1)}
)

# Optimize
xgb_bo.maximize(init_points=5, n_iter=15)

# Best parameters
best_params = xgb_bo.max['params']

# Train the model with the best parameters
best_params['max_depth'] = int(best_params['max_depth'])
best_params['objective'] = 'binary:logistic'
best_params['eval_metric'] = 'logloss'
best_params['silent'] = 1

model = xgb.train(best_params, dtrain, num_boost_round=100)

# Predict on test data
preds = model.predict(dtest)
predictions = [round(value) for value in preds]

# Save model
model.save_model('ml_model_bank_marketing.json')

# Save encoders
with open('encoders_ml_model_bank_marketing.json', 'w') as f:
    json.dump(encoders, f)

print("Model and Encoders saved.")