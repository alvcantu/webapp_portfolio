import pandas as pd
import numpy as np
import mysql.connector
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from bayes_opt import BayesianOptimization
from sklearn.metrics import mean_squared_error


# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor(dictionary=True) # Outputs as dictionary
    return mydb, cursor


sql_query = '''
SELECT 
    InvoiceDate,
    COUNT(DISTINCT TransactionID) AS distinct_transaction_id_count
FROM 
    ONR_DimInvoice i
JOIN 
    ONR_FactTransactions t ON i.InvoiceID = t.InvoiceID
GROUP BY 
    InvoiceDate;
    '''

# Execute the query
mydb, cursor = get_db_connection()
cursor.execute(sql_query)
rows = cursor.fetchall()
df = pd.DataFrame(rows)

# Convert to valid data types
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

# Feature Engineering
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['Day'] = df['InvoiceDate'].dt.day
df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
df['IsWeekend'] = df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
df['Quarter'] = df['InvoiceDate'].dt.quarter
df['Season'] = df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else 
                                         'Spring' if x in [3, 4, 5] else 
                                         'Summer' if x in [6, 7, 8] else 'Autumn')
df['WeekOfMonth'] = df['InvoiceDate'].apply(lambda x: (x.day - 1) // 7 + 1)                                         
# Assuming your fiscal year starts in July
df['FiscalQuarter'] = df['Month'].apply(lambda x: (x - 7) % 12 // 3 + 1)
df['FiscalYear'] = df['Year'] + df['Month'].apply(lambda x: 1 if x >= 7 else 0)                            

# Assume distinct_transaction_id_count is our target variable
X = df[['Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear']]
y = df['distinct_transaction_id_count']

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale the features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Define the function to optimize
def xgb_evaluate(max_depth, learning_rate, n_estimators, gamma, min_child_weight, subsample, colsample_bytree):
    params = {
        'max_depth': int(max_depth),
        'learning_rate': learning_rate,
        'n_estimators': int(n_estimators),
        'gamma': gamma,
        'min_child_weight': min_child_weight,
        'subsample': subsample,
        'colsample_bytree': colsample_bytree,
        'objective': 'reg:squarederror',
        'nthread': 4,
        'seed': 42
    }
    
    # XGBoost model
    model = XGBRegressor(**params)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    
    # We aim to maximize negative MSE (which means minimizing MSE)
    mse = mean_squared_error(y_test, y_pred)
    return -mse  # Bayesian optimization maximizes the function, so we return negative MSE

# Bounds for hyperparameters
xgb_bo = BayesianOptimization(
    xgb_evaluate,
    {
        'max_depth': (3, 10),
        'learning_rate': (0.01, 0.3),
        'n_estimators': (50, 1000),
        'gamma': (0, 1),
        'min_child_weight': (1, 10),
        'subsample': (0.5, 1),
        'colsample_bytree': (0.5, 1)
    }
)

# Perform the optimization
xgb_bo.maximize(init_points=5, n_iter=25)

# Get the best parameters
best_params = xgb_bo.max['params']
best_params['max_depth'] = int(best_params['max_depth'])
best_params['n_estimators'] = int(best_params['n_estimators'])

# Train the final model with best parameters
final_model = XGBRegressor(**best_params)
final_model.fit(X_train_scaled, y_train)

# Predict and evaluate
y_pred_final = final_model.predict(X_test_scaled)
final_mse = mean_squared_error(y_test, y_pred_final)
print(f"Best parameters: {best_params}")
print(f"Final Model MSE: {final_mse}")

# Save the model and scaler for later use
import joblib
joblib.dump(final_model, 'transactions_count_mlmodel_online_retail.joblib')
joblib.dump(scaler, 'transactions_count_scaler_mlmodel_online_retail.joblib')

# Close the connection
cursor.close()
mydb.close()
