import pandas as pd
import mysql.connector
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from datetime import datetime
from skopt import BayesSearchCV
from sklearn.model_selection import TimeSeriesSplit

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

def execute_query(query):
    mydb, cursor = get_db_connection()
    cursor.execute(query)
    # Fetch all rows as a list of dictionaries where keys are column names
    rows = cursor.fetchall()
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(rows)
    
    # Close the connection
    cursor.close()
    mydb.close()
    
    return df

query = '''
SELECT 
    t.InvoiceID AS InvoiceID,
    i.CustomerID AS CustomerID,
    i.InvoiceDate AS InvoiceDate,
    i.Country AS Country,
    t.StockCode AS StockCode,
    t.Description AS Description,
    t.Quantity AS Quantity,
    t.UnitPrice AS UnitPrice,
    (t.Quantity * t.UnitPrice) AS Sales
FROM 
    ONR_FactTransactions t
JOIN 
    ONR_DimInvoice i ON t.InvoiceID = i.InvoiceID;
'''

df = execute_query(query)

# Convert to valid data types
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')
# Feature Engineering
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['Day'] = df['InvoiceDate'].dt.day
df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
df['UnitPrice'] = df['UnitPrice'].fillna(0).astype('float32')

# Encode categorical variables
le = LabelEncoder()
df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
df['Country'] = le.fit_transform(df['Country'])

# Assuming 'Sales' is our target variable
X = df[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']]
y = df['Sales']

# Implement TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=3)  # You can adjust the number of splits

# Bayesian Optimization with skopt
param_space = {
    'max_depth': (6, 12),
    'eta': (0.01, 0.2, 'log-uniform'),
    'min_child_weight': (1, 10),
    'subsample': (0.6, 1.0),
    'colsample_bytree': (0.6, 1.0)
}

model = xgb.XGBRegressor(objective='reg:squarederror')

bayes_search = BayesSearchCV(
    estimator=model, 
    search_spaces=param_space, 
    scoring='neg_mean_squared_error', 
    n_iter=50, 
    cv=tscv,  # Use TimeSeriesSplit for cross-validation
    verbose=1, 
    n_jobs=1  # Set to 1 to avoid memory issues with parallel jobs
)

# Fit the model with Bayesian Optimization
bayes_search.fit(X, y)

# Retrieve the best parameters
best_params = bayes_search.best_params_
print(f"Best parameters found: {best_params}")

# Split data into training and test set based on InvoiceDate
train_date_threshold = datetime(2011, 6, 9)  # Midpoint for split
train_data = df[df['InvoiceDate'] < train_date_threshold]
test_data = df[df['InvoiceDate'] >= train_date_threshold]

X_train = train_data[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']]
y_train = train_data['Sales']
X_test = test_data[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']]
y_test = test_data['Sales']

# Use the best model to predict on the test set
best_model = bayes_search.best_estimator_
predictions = best_model.predict(X_test)

# Evaluate the model
mse = mean_squared_error(y_test, predictions)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, predictions)

print(f"Root Mean Squared Error: {rmse}")
print(f"R-squared Score: {r2}")

# Feature importance
print(best_model.get_booster().get_score(importance_type='gain'))

# Save the best model
best_model.save_model('online_retail/xgboost_salesmodel_online_retail.json')