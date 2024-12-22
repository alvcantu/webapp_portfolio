import pandas as pd
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb

# Future df processing
future_df = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_og = pd.read_csv('online_retail/online_retail_3month_predictions.csv')
future_df_pivoted_perday = pd.read_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv')

# Convert to valid data types
future_df['InvoiceDate'] = pd.to_datetime(future_df['InvoiceDate'])

# Feature Engineering
future_df['Year'] = future_df['InvoiceDate'].dt.year
future_df['Month'] = future_df['InvoiceDate'].dt.month
future_df['Day'] = future_df['InvoiceDate'].dt.day
future_df['DayOfWeek'] = future_df['InvoiceDate'].dt.dayofweek
future_df['IsWeekend'] = future_df['DayOfWeek'].isin([5, 6]).astype(int)  # Saturday or Sunday
future_df['Quarter'] = future_df['InvoiceDate'].dt.quarter
future_df['Season'] = future_df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] else 
                                         'Spring' if x in [3, 4, 5] else 
                                         'Summer' if x in [6, 7, 8] else 'Autumn')

# Encode categorical variables
le = LabelEncoder()
future_df['CustomerID'] = le.fit_transform(future_df['CustomerID'].astype(str))
future_df['StockCode'] = le.fit_transform(future_df['StockCode'].astype(str))
future_df['Country'] = le.fit_transform(future_df['Country'])
future_df['Season'] = le.fit_transform(future_df['Season'])

# Features the model was trained on
features = ['CustomerID', 'StockCode', 'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season', 'Country']

# Import the model
model = xgb.XGBRegressor()
model.load_model('online_retail/attempt2_xgboost_mlmodel_online_retail.json')

# Make predictions
X_future = future_df[features]
predictions_future = model.predict(X_future)

# Adding column with future sales predictions
future_df_og['Predicted_Sales2'] = predictions_future

# Converting Predicted_Sales1 to float and rounding to two decimal places
future_df_og['Predicted_Sales2'] = future_df_og['Predicted_Sales2'].astype(float)
future_df_og['Predicted_Sales2'] = future_df_og['Predicted_Sales2'].round(2)

# Drop feature engineered columns from future_df
future_df = future_df.drop(columns=['Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter', 'Season'])

# Save future_df to a CSV file
future_df_og.to_csv('online_retail/online_retail_3month_predictions.csv', index=False)

# Pivot the future_df to get Predicted_Sales1 per InvoiceDate and save it to a CSV file
future_df_pivoted = pd.pivot_table(future_df_og, 
                          values='Predicted_Sales2', 
                          index='InvoiceDate', 
                          aggfunc='sum')

# Ensure both DataFrames are sorted by this InvoiceDate:
future_df_pivoted_perday = future_df_pivoted_perday.sort_index() 
future_df_pivoted = future_df_pivoted.sort_index()
future_df_pivoted_perday.reset_index(inplace=True)
future_df_pivoted.reset_index(inplace=True)
# Insert Predicted_Sales1 column into the pivoted DataFrame
future_df_pivoted_perday['Total_Predicted_Sales2'] = future_df_pivoted['Predicted_Sales2']
# Save the pivoted DataFrame to original CSV file
future_df_pivoted_perday.to_csv('online_retail/online_retail_pivoted_perday_3month_predictions.csv', index=False)