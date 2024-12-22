import pandas as pd
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
import holidays

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

# Load the CSV with country to holiday_code mapping
country_code_df = pd.read_csv('online_retail/country_mapping_online_retail.csv')
# Future df processing
future_df = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_og = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_pivoted_perday = pd.read_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv')

# Merge the dataframes to get the holiday_code, 
# Mapping assumes all not available countires in holidays as part of Great Britain given its a UK online ratailer
future_df = pd.merge(future_df, country_code_df, on='Country', how='left')

# Convert to valid data types
future_df['InvoiceDate'] = pd.to_datetime(future_df['InvoiceDate'])

# Feature Engineering of InvoiceDate
future_df['Year'] = future_df['InvoiceDate'].dt.year
future_df['Month'] = future_df['InvoiceDate'].dt.month # Assuming your fiscal year starts in July
future_df['Month'] = future_df['InvoiceDate'].dt.month
future_df['Day'] = future_df['InvoiceDate'].dt.day
future_df['DayOfWeek'] = future_df['InvoiceDate'].dt.dayofweek
future_df['IsWeekend'] = future_df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
future_df['Quarter'] = future_df['InvoiceDate'].dt.quarter
future_df['Season'] = future_df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else
                                         'Spring' if x in [3, 4, 5] else
                                         'Summer' if x in [6, 7, 8] else 'Autumn')
future_df['WeekOfMonth'] = future_df['InvoiceDate'].apply(lambda x: (x.day - 1) // 7 + 1)
# Assuming your fiscal year starts in July
future_df['FiscalQuarter'] = future_df['Month'].apply(lambda x: (x - 7) % 12 // 3 + 1)
future_df['FiscalYear'] = future_df['Year'] + future_df['Month'].apply(lambda x: 1 if x >= 7 else 0)
# Apply the function to create the 'IsHoliday' column
future_df['holiday_code'] = future_df['holiday_code'].astype(str)
future_df['IsHoliday'] = future_df.apply(is_holiday, axis=1)

# Additional feature engineering
# Categoize StockCodes
future_df['StockCodeCategory'] = future_df['StockCode'].apply(categorize_stockcode)
future_df['StockCodeLength'] = future_df['StockCode'].str.len()

# Encode categorical variables
le = LabelEncoder()
future_df['CustomerID'] = le.fit_transform(future_df['CustomerID'].astype(str))
future_df['StockCode'] = le.fit_transform(future_df['StockCode'].astype(str))
future_df['Country'] = le.fit_transform(future_df['Country'])
future_df['Season'] = le.fit_transform(future_df['Season'])
future_df['Description'] = le.fit_transform(future_df['Description'])
future_df['StockCodeCategory'] = le.fit_transform(future_df['StockCodeCategory'])
future_df['continent'] = le.fit_transform(future_df['continent'])

# Features the model was trained on
features = ['CustomerID', 'StockCode', 'Country', 'Description', 'StockCodeCategory', 'continent', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'WeekOfMonth', 'FiscalQuarter', 'FiscalYear', 'IsHoliday', 'StockCodeLength']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt4_xgboost_mlmodel_online_retail.json')

# Make predictions
X_future = future_df[features]
predictions_future = model.predict(X_future)

# Adding column with future sales predictions
future_df_og['Predicted_Sales4'] = predictions_future

# Converting Predicted_Sales4 to float and rounding to two decimal places
future_df_og['Predicted_Sales4'] = future_df_og['Predicted_Sales4'].astype(float)
future_df_og['Predicted_Sales4'] = future_df_og['Predicted_Sales4'].round(2)

# Save future_df to a CSV file
future_df_og.to_csv('online_retail/online_retail_3month_predictions.csv', index=False)

# Pivot the future_df to get Predicted_Sales1 per InvoiceDate and save it to a CSV file
future_df_pivoted = pd.pivot_table(future_df_og,
                          values='Predicted_Sales4',
                          index='InvoiceDate',
                          aggfunc='sum')

# Ensure both DataFrames are sorted by this InvoiceDate:
future_df_pivoted_perday = future_df_pivoted_perday.sort_index()
future_df_pivoted = future_df_pivoted.sort_index()
# Drop level 0 column from pivoted DataFrame
#future_df_pivoted_perday.drop(columns=['level_0'], inplace=True)
future_df_pivoted.reset_index(inplace=True)
# Insert Predicted_Sales1 column into the pivoted DataFrame
future_df_pivoted_perday['Total_Predicted_Sales4'] = future_df_pivoted['Predicted_Sales4']

print(future_df_pivoted_perday.head())
# Save the pivoted DataFrame to original CSV file
future_df_pivoted_perday.to_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv', index=False)