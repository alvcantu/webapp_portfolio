import pandas as pd
import mysql.connector
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from datetime import datetime

# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor(dictionary=True)  # This is the key change
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

# Split data based on InvoiceDate
train_date_threshold = datetime(2011, 6, 9)  # Midpoint for split
train_data = df[df['InvoiceDate'] < train_date_threshold]
test_data = df[df['InvoiceDate'] >= train_date_threshold]

X_train = train_data[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']]
y_train = train_data['Sales']
X_test = test_data[['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'UnitPrice', 'Quantity', 'Country']]
y_test = test_data['Sales']

# Prepare data for XGBoost
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# Set up parameters for XGBoost
params = {
    'max_depth': 8,
    'eta': 0.05,
    'objective': 'reg:squarederror',
    'eval_metric': 'rmse',
    'min_child_weight': 1,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}

# Train the model
num_rounds = 300
model = xgb.train(params, dtrain, num_rounds)

# Make predictions
predictions = model.predict(dtest)

# Evaluate the model
mse = mean_squared_error(y_test, predictions)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, predictions)

print(f"Root Mean Squared Error: {rmse}")
print(f"R-squared Score: {r2}")

# Feature importance
print(model.get_score(importance_type='gain'))

# If you want to save the model for later use:
model.save_model('online_retail/xgboost_salesmodel_online_retail.json')
