import pandas as pd
import mysql.connector
from sklearn.metrics import mean_absolute_percentage_error, r2_score
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from datetime import datetime
from bayes_opt import BayesianOptimization
from sklearn.model_selection import TimeSeriesSplit
import holidays

# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor(dictionary=True)
    return mydb, cursor

def execute_query(query):
    mydb, cursor = get_db_connection()
    cursor.execute(query)
    rows = cursor.fetchall()
    df = pd.DataFrame(rows)
    cursor.close()
    mydb.close()
    return df

query = '''
SELECT 
    t.TransactionID AS TransactionID,
    i.CustomerID AS CustomerID,
    i.InvoiceDate AS InvoiceDate,
    i.Country AS Country,
    t.StockCode AS StockCode,
    t.Description AS Description,
    (t.Quantity * t.UnitPrice) AS Sales
FROM 
    ONR_FactTransactions t
JOIN 
    ONR_DimInvoice i ON t.InvoiceID = i.InvoiceID;
'''

df = execute_query(query)

# Load the CSV with country to holiday_code mapping
country_code_df = pd.read_csv('online_retail/country_mapping_online_retail.csv')
# Merge the dataframes to get the holiday_code, 
# Mapping assumes all not available countires in holidays as part of Great Britain given its a UK online ratailer
df = pd.merge(df, country_code_df, on='Country', how='left')

print(df.columns)
# Function to check if it's a holiday
def is_holiday(row):
    country_code = row['holiday_code']
    invoice_date = row['InvoiceDate'].date()  # Get the date part
    
    # Create the holiday calendar for the specified country
    try:
        country_holidays = holidays.CountryHoliday(country_code)
        return True in country_holidays  # Check if the date is a holiday
    except KeyError:
        return False  # If the country code is not supported by the holidays library


# Function to categorize StockCode
def categorize_stockcode(code):
    if code == 'AMAZONFEE' or code == 'BANK CHARGES':
        return 'Fees or bank charges'
    elif code.startswith('DCGSS'):
        return 'party bags'
    elif code.startswith('gift'):
        return 'gift'
    elif code == 'DOT' or code == 'POST':
        return 'Postage costs'
    else:
        return 'Not-classified'


# Convert to valid data types
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

# Feature Engineering of InvoiceDate
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
# Apply the function to create the 'IsHoliday' column
df['holiday_code'] = df['holiday_code'].astype(str)
df['IsHoliday'] = df.apply(is_holiday, axis=1)

# Additional feature engineering
# Categoize StockCodes
# Convert stockcode to string
df['StockCode'] = df['StockCode'].astype(str)
df['StockCodeCategory'] = df['StockCode'].apply(categorize_stockcode)
df['StockCodeLength'] = df['StockCode'].str.len()

# Encode categorical variables
le = LabelEncoder()
df['CustomerID'] = le.fit_transform(df['CustomerID'].astype(str))
df['StockCode'] = le.fit_transform(df['StockCode'].astype(str))
df['Country'] = le.fit_transform(df['Country'])
df['Season'] = le.fit_transform(df['Season'])
df['Description'] = le.fit_transform(df['Description'])
df['StockCodeCategory'] = le.fit_transform(df['StockCodeCategory'])
df['continent'] = le.fit_transform(df['continent'])

# Assuming 'Sales' is our target variable
X = df[['CustomerID', 'StockCode', 'Country', 'Description', 'StockCodeCategory', 'continent', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear', 'IsHoliday', 'StockCodeLength']]
y = df['Sales']

# Time-based split, 70% for training, 30% for testing
train_size = int(len(df) * 0.7)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

# Define the function for Bayesian Optimization
def xgb_evaluate(max_depth, learning_rate, n_estimators, gamma, min_child_weight, subsample, colsample_bytree):
    params = {
        'max_depth': int(max_depth),
        'learning_rate': learning_rate,
        'n_estimators': int(n_estimators),
        'gamma': gamma,
        'min_child_weight': min_child_weight,
        'subsample': subsample,
        'colsample_bytree': colsample_bytree,
        'objective': 'reg:squarederror',  # Note: XGBoost doesn't have a direct MAPE objective
        'n_jobs': -1
    }
    
    # Use TimeSeriesSplit for cross-validation
    tscv = TimeSeriesSplit(n_splits=3)
    model = xgb.XGBRegressor(**params)
    
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    
    # Calculate MAPE
    mape = mean_absolute_percentage_error(y_test, predictions)
    
    return -mape  # Negate MAPE because Bayesian optimization maximizes

# Bounds for Bayesian Optimization
xgbBO = BayesianOptimization(
    xgb_evaluate,
    {
        'max_depth': (3, 12),
        'learning_rate': (0.01, 0.3),
        'n_estimators': (50, 300),
        'gamma': (0, 0.5),
        'min_child_weight': (1, 10),
        'subsample': (0.5, 1),
        'colsample_bytree': (0.5, 1),
    }
)

# Perform the optimization
xgbBO.maximize(init_points=5, n_iter=75)

# Get the best parameters
best_params = xgbBO.max['params']
best_params['max_depth'] = int(best_params['max_depth'])
best_params['n_estimators'] = int(best_params['n_estimators'])

# Train the model with the best parameters
best_model = xgb.XGBRegressor(**best_params)
best_model.fit(X_train, y_train)

# Predict and evaluate
predictions = best_model.predict(X_test)
mape = mean_absolute_percentage_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print(f"Mean Absolute Percentage Error (MAPE): {mape}")
print(f"R-squared Score: {r2}")

# Feature importance
print(best_model.get_booster().get_score(importance_type='gain'))

# Save the best model
best_model.save_model('online_retail/attempt4_xgboost_mlmodel_online_retail.json')